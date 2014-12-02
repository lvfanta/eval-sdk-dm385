/* GStreamer preload library
 * Copyright (C) 2008 Nokia Corporation and its subsidary(-ies)
 *               contact: <stefan.kost@nokia.com>
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Library General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Library General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 51 Franklin Steet,
 * Boston, MA 02110-1301, USA.
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <stdio.h>
#ifdef HAVE_STDLIB_H
#include <stdlib.h>
#endif
#ifdef HAVE_STRING_H
#include <string.h>
#endif
#ifdef HAVE_DLFCN_H
#include <dlfcn.h>
#endif
#ifdef HAVE_UNISTD_H
#include <unistd.h>
#endif
#include <time.h>
#ifdef HAVE_MALLOC_H
#include <malloc.h>
#endif

#ifdef HAVE_SYS_TIME_H
#include <sys/time.h>
#endif
#ifdef HAVE_SYS_RESOURCE_H
#include <sys/resource.h>
#endif

#include <glib.h>
#include <gst/gst.h>

static void *lib_gstreamer;

/* config variables */
static gchar *gsttl_log_name = NULL;
static gboolean gsttl_no_log = FALSE;
static gulong gsttl_log_size = 0;

/* global statistics */
static GHashTable *threads = NULL;
static GHashTable *elements = NULL;
static GHashTable *bins = NULL;
static GHashTable *pads = NULL;
static GHashTable *ghost_pads = NULL;
static guint max_qos = 0;
static gboolean check_cpuload = FALSE;
static guint max_cpuload = 0;
static guint max_memory = 0;
static guint64 num_buffers = 0, num_events = 0, num_messages = 0, num_queries = 0;
static guint num_elements = 0, num_pads = 0;

/* used in _log_common */
static GstClockTime last_ts = G_GUINT64_CONSTANT(0);
static GstClockTime tusersys = G_GUINT64_CONSTANT(0);
static GstClockTime aspent = G_GUINT64_CONSTANT(0);
static GstClockTime areal = G_GUINT64_CONSTANT(0);

#define GSTTL_TIME_AS_SECOND(t) ((gdouble)t/(gdouble)GST_SECOND)

G_LOCK_DEFINE (_stats);

typedef struct {
  /* human readable pad name and details */
  gchar *name;
  guint index;
  GType type;
  GstPadDirection dir;
  /* buffer statistics */
  guint num_buffers;
  guint num_readonly, num_preroll, num_discont, num_gap, num_delta;
  guint min_size,max_size,avg_size;
  /* first and last activity on the pad, expected next_ts */
  GstClockTime first_ts,last_ts, next_ts;
  /* in which thread does it operate */
  gpointer thread_id;
} GsttlPadStats;

typedef struct {
  /* human readable element name */
  gchar *name;
  guint index;
  GType type;
  /* buffer statistics */
  guint recv_buffers, sent_buffers;
  guint64 recv_bytes, sent_bytes;
  /* event, message statistics */
  guint num_events, num_messages, num_queries;
  /* first activity on the element */
  GstClockTime first_ts, last_ts;
  /* time spend in this element */
  GstClockTime treal;
  /* hierarchy */
  GstElement *parent;
} GsttlElementStats;

typedef struct {
  /* time spend in this thread */
  GstClockTime treal;
  guint max_cpuload;
} GsttlThreadStats;

// define category (statically) and set as default
GST_DEBUG_CATEGORY_STATIC (tracelib_debug);
#define GST_CAT_DEFAULT tracelib_debug

/* utillity stuff */

static GstClockTime _priv_start_time=G_GUINT64_CONSTANT(0);

static GstClockTime
_get_timestamp (void)
{
#ifdef HAVE_CLOCK_GETTIME
  struct timespec now;

  clock_gettime (CLOCK_MONOTONIC, &now);
  return GST_TIMESPEC_TO_TIME (now);
#else
  GTimeVal now;

  g_get_current_time (&now);
  return GST_TIMEVAL_TO_TIME (now);
#endif
}

static GstClockTimeDiff
_get_elapsed (void)
{
  return GST_CLOCK_DIFF (_priv_start_time, _get_timestamp ());
}

static FILE *lf = NULL;
static char *lb = NULL;
static gulong lp = 0, ls = 0;

static void
(*_log_entry) (const gchar *fmt, ...) G_GNUC_PRINTF (1, 2) = NULL;

static void
_log_entry_file (const gchar *fmt, ...)
{
  va_list ap;
  
  if(gsttl_no_log)
    return;
  
  if (G_UNLIKELY(!lf)) {
    if (!(lf = fopen (gsttl_log_name, "w"))) {
      fprintf (stderr, "Can't open log file %s : %s", gsttl_log_name, strerror (errno));
      return;
    }
    setlinebuf(stdout);
  }

  va_start(ap, fmt);
  g_vfprintf (lf, fmt, ap);
  va_end(ap);
}

G_LOCK_DEFINE (_mem_logger);

static void
_log_entry_mem (const gchar *fmt, ...)
{
  va_list ap;
  gulong needed;
  
  if(gsttl_no_log)
    return;
  
  va_start(ap, fmt);
  needed = g_printf_string_upper_bound (fmt, ap);
  G_LOCK (_mem_logger);
  if (lp + needed < gsttl_log_size) {
    lp += g_vsprintf (&lb[lp], fmt, ap);
  }
  else {
    if (!ls)
      ls = lp;
    lp += needed;
  }
  G_UNLOCK (_mem_logger);
  va_end(ap);
}

static void
_log_common (GstClockTimeDiff treal)
{
  gpointer thread_id = g_thread_self();
#ifdef HAVE_GETRUSAGE
  guint cpuload = 0;
  struct rusage ru;
  GsttlThreadStats *stats;
  GstClockTimeDiff dreal,dspent;
  GstClockTime tspent;
#endif
#ifdef HAVE_MALLINFO
  struct mallinfo mi;
#endif

  /* we can only trace one process, pid changes messup our timestamps */
  static pid_t last_pid = 0;
  pid_t pid = getpid();
  
  if (pid != last_pid) {
    fprintf (stderr, "pid changed %d -> %d\n", last_pid, pid);
    last_pid = pid;
  }

#ifdef HAVE_GETRUSAGE
  /* self is PID, so this is for all threads */
  getrusage (RUSAGE_SELF,&ru);
  /*
  struct rusage {
    struct timeval ru_utime; // user time used
    struct timeval ru_stime; // system time used
    long   ru_maxrss;        // maximum resident set size - unused
    long   ru_ixrss;         // integral shared memory size - unused
    long   ru_idrss;         // integral unshared data size - unused
    long   ru_isrss;         // integral unshared stack size - unused
    long   ru_minflt;        // page reclaims
    long   ru_majflt;        // page faults
    long   ru_nswap;         // swaps
    long   ru_inblock;       // block input operations
    long   ru_oublock;       // block output operations
    long   ru_msgsnd;        // messages sent
    long   ru_msgrcv;        // messages received
    long   ru_nsignals;      // signals received
    long   ru_nvcsw;         // voluntary context switches
    long   ru_nivcsw;        // involuntary context switches
  };*/

  tspent = GST_TIMEVAL_TO_TIME (ru.ru_utime) + GST_TIMEVAL_TO_TIME (ru.ru_stime);
  dspent = GST_CLOCK_DIFF (tusersys, tspent);
  dreal = GST_CLOCK_DIFF (last_ts, treal);
  tusersys = tspent;

  /* get stats record for current thread */
  if (!(stats = g_hash_table_lookup (threads, thread_id))) {
    stats = g_new0(GsttlThreadStats,1);
    g_hash_table_insert (threads, thread_id, stats);
  }

  /* crude way to meassure time spend in which thread */
  stats->treal += dreal;
  last_ts = treal;

  /* FIXME: how can we take cpu-frequency scaling into account?
   * - looking at /sys/devices/system/cpu/cpu0/cpufreq/
   *   scale_factor=scaling_max_freq/scaling_cur_freq
   * - as a workaround we can switch it via /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
   *   cpufreq-selector -g performance
   *   cpufreq-selector -g ondemand
   */
  if (check_cpuload) {
    /* we only want cpu-load in playing, otherwise max is almost always 100 */
    /* this is the total average, apply a window */
    //cpuload = (guint) gst_util_uint64_scale (tusersys, G_GINT64_CONSTANT(100), treal);
    aspent+=dspent;
    areal+=dreal;
    if(areal > GST_SECOND) {
    //if(areal > (GST_MSECOND*500)) {
      cpuload = (guint) gst_util_uint64_scale (aspent, G_GINT64_CONSTANT(100), areal);
      if (cpuload <= 100) {
        if (cpuload > stats->max_cpuload) {
          stats->max_cpuload = cpuload;
          if (cpuload > max_cpuload) {
            max_cpuload = cpuload;
          }
        }
      }
      else {
        /* this happens during prerolling
        printf("%" GST_TIME_FORMAT " %u\n", GST_TIME_ARGS (treal), cpuload);
        */
      }
      /* reset accumulators */
      aspent = areal = G_GUINT64_CONSTANT(0);
      /* FIXME: use rusage_%p, thread_id ? */
      _log_entry(
        "rusage %" GST_TIME_FORMAT 
        " %lf %u %ld %ld\n",
        GST_TIME_ARGS (treal), GSTTL_TIME_AS_SECOND (treal),
        cpuload, ru.ru_nvcsw, ru.ru_nivcsw);
    }
  }
#endif
#ifdef HAVE_MALLINFO
  mi=mallinfo();

  /* The following fields are defined:
   * `arena' is the total amount of space in the heap;
   * `ordblks' is the number of chunks which are not in use;
   * `uordblks' is the total amount of space allocated by `malloc';
   * `fordblks' is the total amount of space not in use;
   * `keepcost' is the size of the top most memory block.
  struct mallinfo {
    int arena;    // non-mmapped space allocated from system
    int ordblks;  // number of free chunks
    int smblks;   // number of fastbin blocks - unused
    int hblks;    // number of mmapped regions
    int hblkhd;   // space in mmapped regions
    int usmblks;  // maximum total allocated space  - unused
    int fsmblks;  // space available in freed fastbin blocks  - unused
    int uordblks; // total allocated space
    int fordblks; // total free space
    int keepcost; // top-most, releasable (via malloc_trim) space
  }; */
  
  if (mi.uordblks > max_memory) {
    max_memory = mi.uordblks;
  }
  
  _log_entry(
    "mallinfo %" GST_TIME_FORMAT 
    " %lf %d %d %d %d\n",
    GST_TIME_ARGS (treal), GSTTL_TIME_AS_SECOND (treal),
    mi.arena, mi.hblkhd, mi.uordblks, mi.fordblks);
#endif
}

static void
_check_playing(GstElement *element)
{
  if(element && GST_IS_ELEMENT(element))
    check_cpuload=(GST_STATE (element) == GST_STATE_PLAYING);
  else {
    fprintf (stderr, "%p is not an elemnt, it is a %s\n",
      element, G_OBJECT_TYPE_NAME(element));
  }
}

static GsttlElementStats*
_fill_element_stats (GstElement *element)
{
  GsttlElementStats *stats = g_new0(GsttlElementStats,1);
  /* yes we leak the names right now ... */
  stats->name = g_strdup (GST_OBJECT_NAME (element));
  stats->index = num_elements++;
  stats->type = G_OBJECT_TYPE (element);
  stats->first_ts = GST_CLOCK_TIME_NONE;
  return stats;
}

static GsttlElementStats*
_get_bin_stats (GstElement *element)
{
  GsttlElementStats *stats;

  //if(!GST_IS_ELEMENT(element)) G_BREAKPOINT();

  if (!element)
    return NULL;

  G_LOCK (_stats);
  if (!(stats = g_hash_table_lookup (bins, element))) {
    stats = _fill_element_stats(element);
    g_hash_table_insert (bins, element, (gpointer)stats);
  }
  G_UNLOCK (_stats);
  if (stats) {
    if(G_UNLIKELY(!stats->parent)) {
      GstElement *parent = GST_ELEMENT_PARENT (element);
      if(parent) {
        _get_bin_stats (parent);
        stats->parent=parent;
      }
    }
    if(G_UNLIKELY(!stats->name)) {
      if(GST_OBJECT_NAME (element)) {
        stats->name = g_strdup (GST_OBJECT_NAME (element));
      }
    }
  }
  return stats;
}

static GsttlElementStats*
_get_element_stats (GstElement *element)
{
  GsttlElementStats *stats;

  //if(!GST_IS_ELEMENT(element)) G_BREAKPOINT();

  if (!element || GST_IS_BIN(element))
    return NULL;

  G_LOCK (_stats);
  if (!(stats = g_hash_table_lookup (elements, element))) {
    stats = _fill_element_stats(element);
    g_hash_table_insert (elements, element, (gpointer)stats);
  }
  G_UNLOCK (_stats);
  if(G_UNLIKELY(stats && !stats->parent)) {
    GstElement *parent = GST_ELEMENT_PARENT (element);
    if(parent) {
      _get_bin_stats (parent);
      stats->parent=parent;
    }
  }
  return stats;
}

static GsttlPadStats*
_fill_pad_stats (GstPad *pad)
{
  GsttlPadStats *stats = g_new0(GsttlPadStats,1);
  /* yes we leak the names right now ... */
  stats->name = g_strdup_printf ("%s_%s", 
    ((GST_OBJECT_PARENT(pad) != NULL) ? GST_STR_NULL(GST_OBJECT_NAME(GST_OBJECT_PARENT(pad))) : "_" ),
    GST_STR_NULL(GST_OBJECT_NAME(pad)));
  stats->index = num_pads++;
  stats->type = G_OBJECT_TYPE (pad);
  stats->dir = GST_PAD_DIRECTION(pad);
  stats->min_size = G_MAXUINT;
  stats->first_ts = stats->last_ts = stats->next_ts = GST_CLOCK_TIME_NONE;
  stats->thread_id = g_thread_self();
  return stats;
}

static GsttlPadStats*
_get_pad_stats (GstPad *pad)
{
  GsttlPadStats *stats;

  // skip ghost and proxy pads
  if ((!pad) || GST_IS_GHOST_PAD(pad))
    return NULL;

  G_LOCK (_stats);
  if (!(stats = g_hash_table_lookup (pads, pad))) {
    stats = _fill_pad_stats(pad);
    g_hash_table_insert (pads, pad, (gpointer)stats);
  }
  G_UNLOCK (_stats);
  if (GST_IS_ELEMENT(GST_PAD_PARENT (pad))) {
    _get_element_stats (GST_PAD_PARENT (pad));
  }
  return stats;
}

static GsttlPadStats*
_get_ghost_pad_stats (GstPad *pad)
{
  GsttlPadStats *stats;

  // skip non ghost pads
  if ((!pad) || !GST_IS_GHOST_PAD(pad))
    return NULL;

  G_LOCK (_stats);
  if (!(stats = g_hash_table_lookup (ghost_pads, pad))) {
    stats = _fill_pad_stats(pad);
    g_hash_table_insert (ghost_pads, pad, (gpointer)stats);
  }
  G_UNLOCK (_stats);
  _get_element_stats (GST_PAD_PARENT (pad));
  return stats;
}

/* reporting */

static void
_print_pad_stats (gpointer value, gpointer user_data)
{
  GsttlPadStats *stats=(GsttlPadStats *)value;

  if (stats->thread_id == user_data) {
    GstClockTimeDiff running = GST_CLOCK_DIFF (stats->first_ts, stats->last_ts);
    
    printf("    %c %-25s: buffers %7u (ro %5u,pre %3u,dis %5u,gap %5u,dlt %5u),",
      (stats->dir==GST_PAD_SRC)?'>':'<',
      stats->name, stats->num_buffers,
      stats->num_readonly, stats->num_preroll, stats->num_discont, stats->num_gap, stats->num_delta);
    if(stats->min_size == stats->max_size) {
      printf(" size (min/avg/max) ......./%7u/.......,",
        stats->avg_size);
    } else {
      printf(" size (min/avg/max) %7u/%7u/%7u,",
        stats->min_size, stats->avg_size, stats->max_size);
    }
    printf(" time %" GST_TIME_FORMAT ","
      " bytes/sec %lf\n",
      GST_TIME_ARGS (running),
      ((gdouble)(stats->num_buffers*stats->avg_size)*GST_SECOND)/((gdouble)running));
  }
}

static void
_print_thread_stats (gpointer key, gpointer value, gpointer user_data)
{
  GsttlThreadStats *stats=(GsttlThreadStats *)value;
  GSList *list=user_data;
  guint cpuload = 0;
  guint time_percent;
  
  time_percent = (guint) gst_util_uint64_scale (stats->treal, G_GINT64_CONSTANT(100), last_ts);
  
  if(tusersys) {
    guint64 total;
    /* cpuload for the process, scaled by the timeslice of this thread */
    //cpuload = (guint) gst_util_uint64_scale (tusersys, G_GINT64_CONSTANT(100) * stats->treal, last_ts * last_ts);
    
    total = gst_util_uint64_scale (tusersys, G_GINT64_CONSTANT(100), last_ts);
    cpuload = gst_util_uint64_scale (total, stats->treal, last_ts);
  }

  printf("Thread %p Statistics:\n",key);
  printf("  Time: %" GST_TIME_FORMAT ", %u %%\n", GST_TIME_ARGS (stats->treal), (guint)time_percent);
  printf("  Avg/Max CPU load: %u %%, %u %%\n", cpuload, stats->max_cpuload);
  /* FIXME: would be nice to skip, if there are no pads for that thread
   * (e.g. a pipeline), we would need to pass as struct to
   * g_hash_table_foreach::user_data
   */
  puts("  Pad Statistics:");
  //g_hash_table_foreach(pads,_print_pad_stats,key);
  g_slist_foreach(list,_print_pad_stats,key);
}

static void
_print_element_stats (gpointer value, gpointer user_data)
{
  GsttlElementStats *stats=(GsttlElementStats *)value;
  gchar fullname[45+1];
  
  g_snprintf(fullname,45,"%s:%s",g_type_name(stats->type), stats->name);
  
  printf("  %-45s:", fullname);
  if (stats->recv_buffers)
    printf(" buffers in/out %7u", stats->recv_buffers);
  else
    printf(" buffers in/out %7s", "-");
  if (stats->sent_buffers)
    printf("/%7u", stats->sent_buffers);
  else
    printf("/%7s", "-");
  if (stats->recv_bytes)
    printf(" bytes in/out %12" G_GUINT64_FORMAT, stats->recv_bytes);
  else
    printf(" bytes in/out %12s", "-");
  if (stats->sent_bytes)
    printf("/%12" G_GUINT64_FORMAT, stats->sent_bytes);
  else
    printf("/%12s", "-");
  printf(" first activity %" GST_TIME_FORMAT ", "
    " ev/msg/qry sent %5u/%5u/%5u" /*", "
    " cpu usage %u %%"*/
    "\n",
    GST_TIME_ARGS (stats->first_ts),
    stats->num_events, stats->num_messages, stats->num_queries /*,
    (guint)(100*stats->treal/last_ts)*/);
  
}

static void
_accum_element_stats (gpointer value, gpointer user_data)
{
  GsttlElementStats *stats=(GsttlElementStats *)value;

  if (stats->parent) {
    GsttlElementStats *parent_stats = _get_bin_stats (stats->parent);

    parent_stats->num_events += stats->num_events;
    parent_stats->num_messages += stats->num_messages;
    parent_stats->num_queries += stats->num_queries;
    if (!GST_CLOCK_TIME_IS_VALID (parent_stats->first_ts)) {
      parent_stats->first_ts = stats->first_ts;
    }
    else if (GST_CLOCK_TIME_IS_VALID (stats->first_ts)) {
      parent_stats->first_ts = MIN (parent_stats->first_ts, stats->first_ts);
    }
    if (!GST_CLOCK_TIME_IS_VALID (parent_stats->last_ts)) {
      parent_stats->last_ts = stats->last_ts;
    }
    else if (GST_CLOCK_TIME_IS_VALID (stats->last_ts)) {
      parent_stats->last_ts = MAX (parent_stats->last_ts, stats->last_ts);
    }
  }
}

/* sorting */

static gint
_sort_pad_stats_by_first_activity (gconstpointer es1, gconstpointer es2)
{
  return (GST_CLOCK_DIFF (((GsttlPadStats *)es2)->first_ts,((GsttlPadStats *)es1)->first_ts));
}

static void
_sort_pad_stats (gpointer key, gpointer value, gpointer user_data)
{
  GSList **list=user_data;
  
  *list = g_slist_insert_sorted (*list, value, _sort_pad_stats_by_first_activity);
}

static gint
_sort_element_stats_by_first_activity (gconstpointer es1, gconstpointer es2)
{
  return (GST_CLOCK_DIFF (((GsttlElementStats *)es2)->first_ts,((GsttlElementStats *)es1)->first_ts));
}

static void
_sort_element_stats (gpointer key, gpointer value, gpointer user_data)
{
  GSList **list=user_data;
  
  *list = g_slist_insert_sorted (*list, value, _sort_element_stats_by_first_activity);
}

static void
_copy_bin_stats (gpointer key, gpointer value, gpointer user_data)
{
  GHashTable **accum_bins=user_data;
  
  g_hash_table_insert (*accum_bins, key, value);
}

static gboolean
_check_bin_parent (gpointer key, gpointer value, gpointer user_data)
{
  GsttlElementStats *stats=(GsttlElementStats *)value;
  
  return (stats->parent == user_data);
}

static gboolean
_process_leaf_bins (gpointer key, gpointer value, gpointer user_data)
{
  GHashTable *accum_bins = user_data;
  
  if (!g_hash_table_find (accum_bins, _check_bin_parent, key)) {
    _accum_element_stats(value,NULL);
    return TRUE;
  }
  return FALSE;
}

/* wrapped api */

static void
_do_pad_stats(GstPad * pad, GsttlPadStats *stats, GstBuffer *buffer, GstClockTimeDiff elapsed)
{
  guint size = GST_BUFFER_SIZE(buffer);
  GstCaps *pad_caps, *buffer_caps;
  gulong avg_size;
  
  num_buffers++;
  /* size stats */
  avg_size = (((gulong)stats->avg_size * (gulong)stats->num_buffers) + size);
  stats->num_buffers++;
  stats->avg_size = (guint)(avg_size / stats->num_buffers);
  if (size < stats->min_size) stats->min_size=size;
  else if (size > stats->max_size) stats->max_size=size;
  /* time stats */
  if (G_UNLIKELY (!GST_CLOCK_TIME_IS_VALID (stats->first_ts))) stats->first_ts=elapsed;
  stats->last_ts = elapsed;
  /* flag stats */
  if (GST_BUFFER_FLAG_IS_SET (buffer, GST_BUFFER_FLAG_READONLY)) stats->num_readonly++;
  if (GST_BUFFER_FLAG_IS_SET (buffer, GST_BUFFER_FLAG_PREROLL)) stats->num_preroll++;
  if (GST_BUFFER_FLAG_IS_SET (buffer, GST_BUFFER_FLAG_GAP)) stats->num_gap++;
  if (GST_BUFFER_FLAG_IS_SET (buffer, GST_BUFFER_FLAG_DELTA_UNIT)) stats->num_delta++;
  if (GST_BUFFER_FLAG_IS_SET (buffer, GST_BUFFER_FLAG_DISCONT)) {
    stats->num_discont++;
    /* check that there rely is a discont */
    if (stats->next_ts == GST_BUFFER_TIMESTAMP(buffer)) {
      _log_entry(
        "chkts_pad_%s %" GST_TIME_FORMAT " %lf, unexpected timestamp %" GST_TIME_FORMAT " on discont\n",
        stats->name, GST_TIME_ARGS (elapsed), GSTTL_TIME_AS_SECOND (elapsed),
        GST_TIME_ARGS (stats->next_ts));
    }
  } else {
    /* check that there is no discont */
    if (GST_CLOCK_TIME_IS_VALID (stats->next_ts) && GST_BUFFER_TIMESTAMP_IS_VALID (buffer)) {
      if (stats->next_ts != GST_BUFFER_TIMESTAMP(buffer)) {
        _log_entry(
          "chkts_pad_%s %" GST_TIME_FORMAT " %lf, expected timestamp %" GST_TIME_FORMAT ", got %" GST_TIME_FORMAT "\n",
          stats->name, GST_TIME_ARGS (elapsed), GSTTL_TIME_AS_SECOND (elapsed),
          GST_TIME_ARGS (stats->next_ts), GST_TIME_ARGS (GST_BUFFER_TIMESTAMP(buffer)));
      }
    }
  }
  /* update timestamps */
  if (GST_BUFFER_TIMESTAMP_IS_VALID (buffer) + GST_BUFFER_DURATION_IS_VALID (buffer)) {
    stats->next_ts = GST_BUFFER_TIMESTAMP(buffer) + GST_BUFFER_DURATION(buffer);
  } else {
    stats->next_ts = GST_CLOCK_TIME_NONE;
  }
  /* caps sanity checks */
  pad_caps = GST_PAD_CAPS(pad);
  buffer_caps = GST_BUFFER_CAPS(buffer);
  if (pad_caps && !gst_caps_is_fixed(pad_caps)) {
    _log_entry(
      "chkcaps_pad_%s %" GST_TIME_FORMAT " %lf, pad-caps are not fixed\n",
      stats->name, GST_TIME_ARGS (elapsed), GSTTL_TIME_AS_SECOND (elapsed));
  } else if(buffer_caps && !gst_caps_is_fixed(buffer_caps)) {
    _log_entry(
      "chkcaps_pad_%s %" GST_TIME_FORMAT " %lf, buffer-caps are not fixed\n",
      stats->name, GST_TIME_ARGS (elapsed), GSTTL_TIME_AS_SECOND (elapsed));
  } else if (pad_caps && buffer_caps && !gst_caps_is_equal_fixed (pad_caps, buffer_caps)) {
    _log_entry(
      "chkcaps_pad_%s %" GST_TIME_FORMAT " %lf, buffer-caps and pad-caps differ\n",
      stats->name, GST_TIME_ARGS (elapsed), GSTTL_TIME_AS_SECOND (elapsed));
  }
}

static void
_do_transmission_stats(GstPad *pad, GstBuffer *buf, GstClockTimeDiff elapsed)
{
  GstElement *this = GST_PAD_PARENT (pad);
  GsttlElementStats *this_stats = _get_element_stats (this);
  GstPad *peer_pad = GST_PAD_PEER (pad);
  GstObject *parent;
  GsttlElementStats *peer_stats;
  GSList *node,*bin_i_stats=NULL,*bin_o_stats=NULL;

  if (!peer_pad)
    return;

  /* if parent of peer_pad is a pad, then peer_pad is a proxy_pad, where the
   * parent is a ghostpad */
  parent = GST_OBJECT_PARENT (peer_pad);
  while (parent && GST_IS_PAD (parent)) {
    peer_pad = GST_PAD (parent);
    /* if this is now the ghost pad, get the peer of this */
    if (GST_IS_GHOST_PAD (peer_pad)) {
      _get_ghost_pad_stats (peer_pad);
      if (parent = GST_OBJECT_PARENT (peer_pad)) {
        peer_stats = _get_bin_stats (GST_ELEMENT(parent));
        bin_o_stats = g_slist_prepend (bin_o_stats, peer_stats);
      }
      peer_pad = GST_PAD_PEER (GST_GHOST_PAD (peer_pad));
      parent = GST_OBJECT_PARENT (peer_pad);
    }
    else {
      fprintf (stderr, "%" GST_TIME_FORMAT " parent of proxy pad %s_%s is not a ghostpad\n",
        GST_TIME_ARGS(elapsed), GST_DEBUG_PAD_NAME (peer_pad));
      return;
    }
  }
  /* if peer_pad is a ghost-pad, then parent is a bin an it is the parent of
   * a proxy_pad */
  while (GST_IS_GHOST_PAD(peer_pad)) {
    _get_ghost_pad_stats (peer_pad);
    peer_stats = _get_bin_stats (GST_ELEMENT(parent));
    bin_i_stats = g_slist_prepend (bin_i_stats, peer_stats);
    peer_pad = gst_ghost_pad_get_target (GST_GHOST_PAD(peer_pad));
    parent = GST_OBJECT_PARENT (peer_pad);
  }

  if (!parent) {
    fprintf (stderr,"%" GST_TIME_FORMAT " transmission on unparented target pad%s_%s\n",
      GST_TIME_ARGS(elapsed), GST_DEBUG_PAD_NAME (peer_pad));
    return;
  }
  peer_stats = _get_element_stats (GST_ELEMENT(parent));
  
  if(GST_PAD_DIRECTION(pad) == GST_PAD_SRC) {
    /* push */
    this_stats->sent_buffers++;
    peer_stats->recv_buffers++;
    this_stats->sent_bytes += GST_BUFFER_SIZE(buf);
    peer_stats->recv_bytes += GST_BUFFER_SIZE(buf);
    /* time stats */
    if (G_UNLIKELY (!GST_CLOCK_TIME_IS_VALID (this_stats->first_ts))) {
      this_stats->first_ts=elapsed;
      //printf("%" GST_TIME_FORMAT " %s pushes on %s\n",GST_TIME_ARGS(elapsed),this_stats->name,peer_stats->name);
    }
    if (G_UNLIKELY (!GST_CLOCK_TIME_IS_VALID (peer_stats->first_ts))) {
      peer_stats->first_ts=elapsed+1;
      //printf("%" GST_TIME_FORMAT " %s is beeing pushed from %s\n",GST_TIME_ARGS(elapsed),peer_stats->name,this_stats->name);
    }
    for (node = bin_o_stats; node; node = g_slist_next(node)) {
      peer_stats = node->data;
      peer_stats->sent_buffers++;
      peer_stats->sent_bytes += GST_BUFFER_SIZE(buf);
    }
    for (node = bin_i_stats; node; node = g_slist_next(node)) {
      peer_stats = node->data;
      peer_stats->recv_buffers++;
      peer_stats->recv_bytes += GST_BUFFER_SIZE(buf);
    }
  } else {
    /* pull */
    peer_stats->sent_buffers++;
    this_stats->recv_buffers++;
    peer_stats->sent_bytes += GST_BUFFER_SIZE(buf);
    this_stats->recv_bytes += GST_BUFFER_SIZE(buf);
    /* time stats */
    if (G_UNLIKELY (!GST_CLOCK_TIME_IS_VALID (this_stats->first_ts))) {
      this_stats->first_ts=elapsed+1;
      //printf("%" GST_TIME_FORMAT " %s pulls from %s\n",GST_TIME_ARGS(elapsed),this_stats->name,peer_stats->name);
    }
    if (G_UNLIKELY (!GST_CLOCK_TIME_IS_VALID (peer_stats->first_ts))) {
      peer_stats->first_ts=elapsed;
      //printf("%" GST_TIME_FORMAT " %s is beeing pulled from %s\n",GST_TIME_ARGS(elapsed),peer_stats->name,this_stats->name);
    }
    for (node = bin_i_stats; node; node = g_slist_next(node)) {
      peer_stats = node->data;
      peer_stats->sent_buffers++;
      peer_stats->sent_bytes += GST_BUFFER_SIZE(buf);
    }
    for (node = bin_o_stats; node; node = g_slist_next(node)) {
      peer_stats = node->data;
      peer_stats->recv_buffers++;
      peer_stats->recv_bytes += GST_BUFFER_SIZE(buf);
    }
  }
  g_slist_free (bin_o_stats);
  g_slist_free (bin_i_stats);
}

static void
_do_element_stats(GstPad *pad, GstClockTimeDiff elapsed1, GstClockTimeDiff elapsed2)
{
  GstClockTimeDiff elapsed = GST_CLOCK_DIFF (elapsed1,elapsed2);
  GstElement *this = GST_PAD_PARENT (pad);
  GsttlElementStats *this_stats = _get_element_stats (this);
  GstPad *peer_pad = GST_PAD_PEER (pad);
  GstObject *parent;
  GsttlElementStats *peer_stats;

  if (!peer_pad)
    return;

  /* if parent of peer_pad is a pad, then peer_pad is a proxy_pad, where the
   * parent is a ghostpad */
  parent = GST_OBJECT_PARENT (peer_pad);
  while(parent && GST_IS_PAD(parent)) {
    peer_pad = GST_PAD(parent);
    /* if this is now the ghost pad, get the peer of this */
    if (GST_IS_GHOST_PAD(peer_pad)) {
      _get_ghost_pad_stats (peer_pad);
      if (parent = GST_OBJECT_PARENT (peer_pad)) {
        _get_bin_stats (GST_ELEMENT(parent));
      }
      peer_pad = GST_PAD_PEER(GST_GHOST_PAD(peer_pad));
      parent = GST_OBJECT_PARENT (peer_pad);
    }
    else {
      GsttlPadStats *pad_stats=_get_pad_stats (pad);
  
      printf("%" GST_TIME_FORMAT " parent of proxy pad %s_%s is not a ghostpad\n",
        GST_TIME_ARGS(elapsed), GST_DEBUG_PAD_NAME (peer_pad));
      return;
    }
  }
  /* if peer_pad is a ghost-pad, then parent is a bin an it is the parent of
   * a proxy_pad */
  while (GST_IS_GHOST_PAD(peer_pad)) {
    _get_ghost_pad_stats (peer_pad);
    _get_bin_stats (GST_ELEMENT(parent));
    peer_pad = gst_ghost_pad_get_target (GST_GHOST_PAD(peer_pad));
    parent = GST_OBJECT_PARENT (peer_pad);
  }

  if (!parent) {
    GsttlPadStats *pad_stats=_get_pad_stats (pad);

    printf("%" GST_TIME_FORMAT " transmission on unparented target pad %s -> %s_%s\n",
      GST_TIME_ARGS(elapsed), pad_stats->name, GST_DEBUG_PAD_NAME (peer_pad));
    return;
  }
  peer_stats = _get_element_stats (GST_ELEMENT(parent));

  /* we'd like to gather time spend in each element, but this does not make too
   * much sense yet
   * pure push/pull-based:
   *   - the time spend in the push/pull_range is accounted for the peer and
   *     removed from the current element
   *   - this works for chains
   *   - drawback is sink elements that block to sync have a high time usage
   *     - we could rerun the ests with sync=false
   * both:
   *   - a.g. demuxers both push and pull. thus we subtract time for the pull
   *     and the push operations, but never add anything.
   *   - can we start a counter after push/pull in such elements and add then
   *     time to the element upon next pad activity?
   */
#if 1
  /* this does not make sense for demuxers */
  this_stats->treal -= elapsed;
  peer_stats->treal += elapsed;
#else
  /* this creates several >100% figures */
  this_stats->treal += GST_CLOCK_DIFF (this_stats->last_ts, elapsed2) - elapsed;
  peer_stats->treal += elapsed;
  this_stats->last_ts = elapsed2;
  peer_stats->last_ts = elapsed2;
#endif
}

static GstFlowReturn (*orig_pad_push) (GstPad *,GstBuffer *) = NULL;

GstFlowReturn
gst_pad_push (GstPad *pad, GstBuffer *buffer)
{
  GstClockTimeDiff elapsed1 = _get_elapsed();
  GstClockTimeDiff elapsed2, sched_jitter;
  GsttlPadStats *stats = _get_pad_stats (pad);
  GstFlowReturn ret;
  GstObject *parent;
  
  if(!stats)
    return orig_pad_push (pad, buffer);

  if (GST_CLOCK_TIME_IS_VALID (stats->last_ts)) {
    sched_jitter = GST_CLOCK_DIFF (stats->last_ts, elapsed1);
    _log_entry(
      "pad_%s %" GST_TIME_FORMAT " %lf %u %" G_GUINT64_FORMAT " %lf\n",
      stats->name, GST_TIME_ARGS (elapsed1), GSTTL_TIME_AS_SECOND (elapsed1),
      GST_BUFFER_SIZE (buffer), GST_BUFFER_OFFSET (buffer),
      GSTTL_TIME_AS_SECOND (sched_jitter));
  } else {
    _log_entry(
      "pad_%s %" GST_TIME_FORMAT " %lf %u %" G_GUINT64_FORMAT "\n",
      stats->name, GST_TIME_ARGS (elapsed1), GSTTL_TIME_AS_SECOND (elapsed1),
      GST_BUFFER_SIZE (buffer), GST_BUFFER_OFFSET (buffer));
  }

  /* switch cpu-load logging on/off */
  parent = GST_OBJECT_PARENT (pad);
  while (parent && GST_IS_PAD (parent)) {
    parent = GST_OBJECT_PARENT (parent);
  }
  _check_playing (GST_ELEMENT(parent));

  /* statistics */
  _do_pad_stats(pad, stats, buffer, elapsed1);
  _do_transmission_stats(pad, buffer, elapsed1);

  _log_common (elapsed1);
  ret = orig_pad_push (pad, buffer);
  elapsed2 = _get_elapsed();
  _log_common (elapsed2);
  
  /* statistics */
  _do_element_stats(pad, elapsed1, elapsed2);

  return ret;
}

static gboolean (*orig_pad_pull_range) (GstPad *, guint64, guint, GstBuffer **) = NULL;

GstFlowReturn
gst_pad_pull_range (GstPad * pad, guint64 offset, guint size, GstBuffer ** buffer)
{
  GstClockTimeDiff elapsed1 = _get_elapsed();
  GstClockTimeDiff elapsed2, sched_jitter;
  GsttlPadStats *stats = _get_pad_stats (pad);
  GstFlowReturn ret;
  GstObject *parent;

  if(!stats)
    return orig_pad_pull_range (pad, offset, size, buffer);

  if (GST_CLOCK_TIME_IS_VALID (stats->last_ts)) {
    sched_jitter = GST_CLOCK_DIFF (stats->last_ts, elapsed1);
    _log_entry(
      "pad_%s %" GST_TIME_FORMAT " %lf %u %" G_GUINT64_FORMAT" %lf\n",
      stats->name, GST_TIME_ARGS (elapsed1), GSTTL_TIME_AS_SECOND (elapsed1),
      size, offset,
      GSTTL_TIME_AS_SECOND (sched_jitter));
  } else {
    _log_entry(
      "pad_%s %" GST_TIME_FORMAT " %lf %u %" G_GUINT64_FORMAT "\n",
      stats->name, GST_TIME_ARGS (elapsed1), GSTTL_TIME_AS_SECOND (elapsed1),
      size, offset);
  }

  /* switch cpu-load logging on/off */
  parent = GST_OBJECT_PARENT (pad);
  while (parent && GST_IS_PAD (parent)) {
    parent = GST_OBJECT_PARENT (parent);
  }
  _check_playing (GST_ELEMENT(parent));

  _log_common (elapsed1);
  ret = orig_pad_pull_range (pad, offset, size, buffer);
  elapsed2 = _get_elapsed();
  _log_common (elapsed2);

  /* statistics */
  _do_pad_stats(pad, stats, *buffer, elapsed2);
  _do_transmission_stats(pad, *buffer, elapsed2);
  _do_element_stats(pad, elapsed1, elapsed2);
  return ret;
}

static gboolean (*orig_pad_send_event) (GstPad *, GstEvent *);

gboolean
gst_pad_send_event (GstPad *pad, GstEvent *event)
{
  GstClockTimeDiff elapsed = _get_elapsed();
  GstObject *parent;
  GstElement *element;
  GsttlElementStats *stats;
  GstPad *real_pad = pad;
  GstPad *peer_pad = GST_PAD_PEER (pad);
  GsttlPadStats *pad_stats,*peer_pad_stats;
  gboolean ret;

  parent = GST_OBJECT_PARENT (real_pad);
  /* if parent of pad is a pad, then pad is a proxy_pad, where the parent is a
   * ghostpad */
  while (parent && GST_IS_PAD (parent)) {
    real_pad = GST_PAD (parent);
    parent = GST_OBJECT_PARENT (real_pad);
  }
  /* if pad is a ghost-pad, then parent is a bin an it is the parent of a
   * proxy_pad */
  while (GST_IS_GHOST_PAD (real_pad)) {
    real_pad = gst_ghost_pad_get_target (GST_GHOST_PAD (real_pad));
    parent = GST_OBJECT_PARENT (real_pad);
  }
  if(element = GST_ELEMENT (parent)) {
    stats = GST_IS_BIN (element) ? _get_bin_stats (element) : _get_element_stats (element);
    pad_stats = (GST_IS_GHOST_PAD (pad)) ? _get_ghost_pad_stats (pad) : _get_pad_stats (pad);
    peer_pad_stats = (GST_IS_GHOST_PAD (peer_pad)) ? _get_ghost_pad_stats (peer_pad) : _get_pad_stats (peer_pad);

    if(!peer_pad_stats) {
      fprintf (stderr,"%" GST_TIME_FORMAT " event %s send to unlinked pad %s_%s\n",
          GST_TIME_ARGS(elapsed), GST_EVENT_TYPE_NAME(event),
          GST_DEBUG_PAD_NAME (pad));
      peer_pad_stats = pad_stats;
    }

    switch (GST_EVENT_TYPE (event)) {
      case GST_EVENT_QOS: {
        gdouble proportion;
        guint qos;

        gst_event_parse_qos (event, &proportion, NULL, NULL);
        qos = (guint)(proportion * 100);
        if (qos > max_qos) {
          /* printf("%" GST_TIME_FORMAT " %u\n", GST_TIME_ARGS (elapsed), qos);*/
          max_qos = qos;
        }
        _log_entry(
          "ev_qos %" GST_TIME_FORMAT " %lf %u %s %u %s %u\n",
          GST_TIME_ARGS (elapsed), GSTTL_TIME_AS_SECOND (elapsed),
          pad_stats->index, pad_stats->name, 
          peer_pad_stats->index, peer_pad_stats->name, qos);
      } break;
      default:
        _log_entry(
          "ev_%s %" GST_TIME_FORMAT " %lf %u %s %u %s\n",
          GST_EVENT_TYPE_NAME(event),
          GST_TIME_ARGS (elapsed), GSTTL_TIME_AS_SECOND (elapsed), 
          pad_stats->index, pad_stats->name, 
          peer_pad_stats->index, peer_pad_stats->name);
        break;
    }
    stats->num_events++;
    num_events++;
  
    /* switch cpu-load logging on/off */
    _check_playing (element);
  }

  _log_common(elapsed);
  ret = orig_pad_send_event (pad, event);
  elapsed = _get_elapsed();
  _log_common(elapsed);
  
  return ret;
}

static gboolean (*orig_element_post_message) (GstElement *, GstMessage *);

gboolean
gst_element_post_message (GstElement *element, GstMessage *message)
{
  GstClockTimeDiff elapsed = _get_elapsed();
  GsttlElementStats *stats;
  gboolean ret;

  stats = GST_IS_BIN (element) ? _get_bin_stats (element) : _get_element_stats (element);

  switch (GST_MESSAGE_TYPE (message)) {
    case GST_MESSAGE_STATE_CHANGED: {
      GstState oldstate, newstate;
      gst_message_parse_state_changed (message, &oldstate, &newstate, NULL);
      _log_entry(
        "msg_%s %" GST_TIME_FORMAT " %lf %u %s %s->%s\n",
        GST_MESSAGE_TYPE_NAME (message), GST_TIME_ARGS (elapsed), GSTTL_TIME_AS_SECOND (elapsed),
        stats->index, stats->name,
        gst_element_state_get_name(oldstate),
        gst_element_state_get_name(newstate));
      break;
    }
    default:
      _log_entry(
        "msg_%s %" GST_TIME_FORMAT " %lf %u %s \n",
        GST_MESSAGE_TYPE_NAME (message), GST_TIME_ARGS (elapsed), GSTTL_TIME_AS_SECOND (elapsed),
        stats->index, stats->name);
      break;
  }
  stats->num_messages++;
  num_messages++;

  /* switch cpu-load logging on/off */
  _check_playing (element);

  _log_common(elapsed);
  ret = orig_element_post_message (element, message);
  elapsed = _get_elapsed();
  _log_common(elapsed);
  
  return ret;
}

static gboolean (*orig_element_query) (GstElement *, GstQuery *);

gboolean
gst_element_query (GstElement *element, GstQuery *query)
{
  GstClockTimeDiff elapsed = _get_elapsed();
  GsttlElementStats *stats;
  gboolean ret;

  stats = GST_IS_BIN (element) ? _get_bin_stats (element) : _get_element_stats (element);

  stats->num_queries++;
  num_queries++;

  _log_entry(
    "qry_%s %" GST_TIME_FORMAT " %lf %u %s \n",
    GST_QUERY_TYPE_NAME (query), GST_TIME_ARGS (elapsed), GSTTL_TIME_AS_SECOND (elapsed),
    stats->index, stats->name);

  /* switch cpu-load logging on/off */
  _check_playing (element);

  _log_common(elapsed);
  ret = orig_element_query (element, query);
  elapsed = _get_elapsed();
  _log_common(elapsed);
  
  return ret;

}

static GstCaps * (*orig_pad_get_caps) (GstPad *);

GstCaps *
gst_pad_get_caps (GstPad *pad)
{
  GstClockTimeDiff elapsed = _get_elapsed();
  GsttlPadStats *pad_stats;
  GstCaps *ret;

  pad_stats = (GST_IS_GHOST_PAD (pad)) ? _get_ghost_pad_stats (pad) : _get_pad_stats (pad);

  if (pad_stats) {
    _log_entry(
      "get_caps %" GST_TIME_FORMAT " %lf %u %s\n",
          GST_TIME_ARGS (elapsed), GSTTL_TIME_AS_SECOND (elapsed),
          pad_stats->index, pad_stats->name);
  }

  _log_common(elapsed);
  ret = orig_pad_get_caps (pad);
  elapsed = _get_elapsed();
  _log_common(elapsed);

  return ret;
}

static gboolean (*orig_pad_set_caps) (GstPad *, GstCaps *);

gboolean
gst_pad_set_caps (GstPad *pad, GstCaps *caps)
{
  GstClockTimeDiff elapsed = _get_elapsed();
  GsttlPadStats *pad_stats;
  gboolean ret;

  pad_stats = (GST_IS_GHOST_PAD (pad)) ? _get_ghost_pad_stats (pad) : _get_pad_stats (pad);

  /* caps size should be 1 when starting up and caps==NULL when stopping */
  if (pad_stats) {
    _log_entry(
      "set_caps %" GST_TIME_FORMAT " %lf %u %s %d\n",
          GST_TIME_ARGS (elapsed), GSTTL_TIME_AS_SECOND (elapsed),
          pad_stats->index, pad_stats->name,
          (caps ? gst_caps_get_size(caps) : 0));
  }
  
#if 0
  if (gst_caps_is_equal_fixed(GST_PAD_CAPS(pad),caps)) {
    printf ("Broken element: setting same caps on pad: %s, caps: %" GST_PTR_FORMAT "\n",
      pad_stats->name, caps);
  }
#endif

  _log_common(elapsed);
  ret = orig_pad_set_caps (pad, caps);
  elapsed = _get_elapsed();
  _log_common(elapsed);

  return ret;
}

/* preloading helper */

static void
_save_symbol(void *lib, void **orig, const gchar *name)
{
  gchar *errstr;

  if (!(*orig = dlsym (lib, name))) {
    errstr = dlerror ();
    g_critical ("Failed to find %s() in gstreamer library: %s, aborting..",
      name, errstr ? errstr : "<Symbol is NULL>");
    exit (1);
  }
}

/* init/free */

static void
#if __GNUC__ > 2 || (__GNUC__ == 2 && __GNUC_MINOR__ > 4)
__attribute__ ((constructor))
#endif /* !__GNUC__ */
gst_preload_init (void)
{
  gchar *log_size;

  if (!g_thread_supported ())
    g_thread_init (NULL);
  g_type_init ();

  gst_init(NULL,NULL);

  GST_DEBUG_CATEGORY_INIT (tracelib_debug, PACKAGE_NAME, 0, PACKAGE_STRING);

  /* get configuration */
  if(!(gsttl_log_name = getenv ("GSTTL_LOG_NAME"))) {
    /* use g_get_tmp_dir() ? */
    gsttl_log_name = "/gsttl.log";
  }
  if(getenv ("GSTTL_NO_LOG")) {
    gsttl_no_log=TRUE;
  }
  if((log_size = getenv ("GSTTL_LOG_SIZE"))) {
    gsttl_log_size = atol (log_size);
  }
  if(!gsttl_log_size) {
    _log_entry=_log_entry_file;
  } else {
    _log_entry=_log_entry_mem;
    lb = g_malloc (gsttl_log_size);
  }

  /* init structures to gather stats */
  threads = g_hash_table_new_full (NULL,NULL,NULL,(GDestroyNotify)g_free);
  elements = g_hash_table_new_full (NULL,NULL,NULL,(GDestroyNotify)g_free);
  bins = g_hash_table_new_full (NULL,NULL,NULL,(GDestroyNotify)g_free);
  pads = g_hash_table_new_full (NULL,NULL,NULL,(GDestroyNotify)g_free);
  ghost_pads = g_hash_table_new_full (NULL,NULL,NULL,(GDestroyNotify)g_free);

  /* load library (abort if not found) */
  lib_gstreamer = dlopen ("libgstreamer-0.10.so", RTLD_LAZY);
  if (!lib_gstreamer)
    lib_gstreamer = dlopen ("libgstreamer-0.10.so.0", RTLD_LAZY);
  if (!lib_gstreamer) {
    const gchar *errstr = dlerror ();
    g_critical ("Failed to load gstreamer library: %s, aborting..",
      errstr ? errstr : "<No error details>");
    exit (1);
  }

  /* get pointer to original functions to chain up */
  _save_symbol (lib_gstreamer, (void **)(void *)&orig_pad_push, "gst_pad_push");
  _save_symbol (lib_gstreamer, (void **)(void *)&orig_pad_pull_range, "gst_pad_pull_range");
  _save_symbol (lib_gstreamer, (void **)(void *)&orig_pad_send_event, "gst_pad_send_event");
  _save_symbol (lib_gstreamer, (void **)(void *)&orig_element_post_message, "gst_element_post_message");
  _save_symbol (lib_gstreamer, (void **)(void *)&orig_element_query, "gst_element_query");
  _save_symbol (lib_gstreamer, (void **)(void *)&orig_pad_get_caps, "gst_pad_get_caps");
  _save_symbol (lib_gstreamer, (void **)(void *)&orig_pad_set_caps, "gst_pad_set_caps");

  /* we'd like to sync gst-tracelib logs and gst debug logs,
   * one can sync timestamps in gst-tracelib logs with debug logs by adding the
   * timestamp of the logline to the timestamp in a tracelib log */
#if 0
  /* enforce log level and write a sync timestamp */
  gst_debug_category_set_threshold (tracelib_debug, GST_LEVEL_WARNING);
  _priv_start_time = _get_timestamp ();
  GST_WARNING("timestamp-sync");
  gst_debug_category_reset_threshold (tracelib_debug);
#else
  /* just log en event called "sync_times", no need for debug-viewer to parse
   * the log for a special event then. We also log a zero first to not confuse
   * the plot script.
   */
  _priv_start_time = _get_timestamp ();
  _log_entry ("sync_times %" GST_TIME_FORMAT ", %" GST_TIME_FORMAT " %lf\n",
      GST_TIME_ARGS (G_GUINT64_CONSTANT (0)),
      GST_TIME_ARGS (_priv_start_time),
      GSTTL_TIME_AS_SECOND (_priv_start_time));
#endif
}

static void
#if __GNUC__ > 2 || (__GNUC__ == 2 && __GNUC_MINOR__ > 4)
__attribute__ ((destructor))
#endif /* !__GNUC__ */
gst_preload_done (void)
{
  GstClockTimeDiff treal = _get_elapsed();
  guint cpuload = 0;

  if(!last_ts)
    goto done;
  
  if(tusersys) {
    cpuload = (guint) gst_util_uint64_scale (tusersys, G_GINT64_CONSTANT(100), last_ts);
  }

  /* print overall stats */
  puts("\nOverall Statistics:");
  printf("Number of Threads: %u\n", g_hash_table_size(threads));
  printf("Number of Elements: %u\n", num_elements);
  printf("Number of Bins: %u\n", g_hash_table_size(bins));
  printf("Number of Pads: %u\n", num_pads);
  printf("Number of GhostPads: %u\n",g_hash_table_size(ghost_pads));
  printf("Number of Buffers passed: %"G_GUINT64_FORMAT"\n",num_buffers);
  printf("Number of Events sent: %"G_GUINT64_FORMAT"\n",num_events);
  printf("Number of Message sent: %"G_GUINT64_FORMAT"\n",num_messages);
  printf("Number of Queries sent: %"G_GUINT64_FORMAT"\n",num_queries);
  printf("Time: %" GST_TIME_FORMAT "\n", GST_TIME_ARGS (last_ts));
  printf("Avg/Max CPU load: %u %%, %u %%\n", cpuload, max_cpuload);
  printf("Max QOS ratio: %u %%\n", max_qos);
  printf("Max Memory usage: %u kb\n\n", max_memory);
  
  /* foreach pad */
  if (g_hash_table_size(threads)) {
    GSList *list=NULL;

    g_hash_table_foreach(pads,_sort_pad_stats,&list);
    //g_slist_foreach(list,_print_thread_stats, NULL);
    g_hash_table_foreach(threads,_print_thread_stats,list);
    puts("");
    g_slist_free(list);
  }

  /* foreach element */
  if (g_hash_table_size(elements)) {
    GSList *list=NULL;
    
    puts("Element Statistics:");
    /* sort by first_activity */
    g_hash_table_foreach(elements,_sort_element_stats,&list);
    /* attribute element stats to bins */
    g_slist_foreach(list,_accum_element_stats, NULL);
    g_slist_foreach(list,_print_element_stats, NULL);
    puts("");
    g_slist_free(list);
  }

  /* foreach bin */
  if (g_hash_table_size(bins)) {
    GSList *list=NULL;
    GHashTable *accum_bins = g_hash_table_new_full (NULL,NULL,NULL,NULL);

    puts("Bin Statistics:");
    /* attribute bin stats to parent-bins */
    g_hash_table_foreach (bins, _copy_bin_stats, &accum_bins);
    while(g_hash_table_size (accum_bins)) {
      g_hash_table_foreach_remove (accum_bins, _process_leaf_bins, accum_bins);
    }
    g_hash_table_destroy (accum_bins);
    /* sort by first_activity */
    g_hash_table_foreach(bins,_sort_element_stats,&list);
    g_slist_foreach(list,_print_element_stats, NULL);
    puts("");
    g_slist_free(list);
  }

done:
  /* free ressources */
  if(!gsttl_log_size) {
    if(lf) fclose (lf);
  } else {
    if (lp > gsttl_log_size) {
      fprintf (stderr, "Log buffer was too small; %lu given, but %lu needed\n", gsttl_log_size, lp);
      lp = ls;
    }
    if (!(lf = fopen (gsttl_log_name, "w"))) {
      fprintf (stderr, "Can't open log file %s : %s", gsttl_log_name, strerror (errno));
    } else {
      fwrite (lb, lp, 1, lf);
      fclose (lf);
    }
    g_free (lb);
  }
  g_hash_table_destroy (ghost_pads);
  g_hash_table_destroy (pads);
  g_hash_table_destroy (bins);
  g_hash_table_destroy (elements);
  g_hash_table_destroy (threads);
  
  if(lib_gstreamer)
    dlclose (lib_gstreamer);
}
