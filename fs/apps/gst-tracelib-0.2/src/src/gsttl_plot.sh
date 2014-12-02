#!/bin/bash
# dumps a gnuplot script to stdout that does a multiplot of the given logs

usage="\
Usage: gsttl_plot.sh [--title=<title>] [--base==<basedir>] [--format={png,pdf,ps,svg}] [--pagesize={a3,a4}]| gnuplot"

# default options
title="GStreamer profile"
base="gsttl"
format="png"
pagesize="a4"

# process commandline options
# @todo: add support for single letter options
while true; do
  case "X$1" in
    X--version) echo "0.1"; exit 0;;
    X--help) echo "$usage"; exit 0;;
    X--title=*) title=`echo $1 | sed s/.*=//`; shift;;
    X--base=*) base=`echo $1 | sed s/.*=//`; shift;;
    X--format=*) format=`echo $1 | sed s/.*=//`; shift;;
    X--pagesize=*) pagesize=`echo $1 | sed s/.*=//`; shift;;
    X--*) shift;;
    X*) break;;
  esac
done

# sanity checks
if [ ! -e $base ]; then
  echo "Error: No datafiles in $base";
  echo "${usage}" 1>&2
  exit 1
fi

# calculate layout
num_padlogs=`ls -1 $base/pad*.log | wc -l`
# we had 1 plot for each pad in first column and 3 extra plot on the 2nd column
plot_height1=$((num_padlogs*300))
plot_height2=$((3*300+2*2*300+2*3*300))
plot_height=$plot_height1
if [ $plot_height -lt $plot_height2 ]; then
  plot_height=$((plot_height2+100));
fi

height1=`echo "scale=4;290.0/$plot_height2" | bc`
height2=`echo "scale=4;$height1*2.0" | bc`
height3=`echo "scale=4;$height1*3.0" | bc`
plt_perf_origin=`echo "scale=4;1.0-($height1*1.0)" | bc`
plt_rusage_origin=`echo "scale=4;1.0-($height1*2.0)" | bc`
plt_memory_origin=`echo "scale=4;1.0-($height1*3.0)" | bc`
plt_caps_origin=`echo "scale=4;1.0-($height1*6.0)" | bc`
plt_ev_origin=`echo "scale=4;1.0-($height1*9.0)" | bc`
plt_msg_origin=`echo "scale=4;1.0-($height1*11.0)" | bc`
plt_qry_origin=`echo "scale=4;1.0-($height1*13.0)" | bc`

last_ts=`tail -qn1 $base/*.log | cut -d' ' -f2 | sort -n | tail -n1`

# debugging
cat <<EOF
# page height  : $plot_height1 , $plot_height2 : $plot_height
# graph height : $height1
EOF

# configure output
# http://en.wikipedia.org/wiki/Paper_size
case $pagesize in
  a3) page_with="29.7 cm";page_height="42.0 cm";;
  a4) page_with="21.0 cm";page_height="29.7 cm";;
esac
# http://www.gnuplot.info/docs/node341.html (terminal options)
case $format in
  # this doen't like fonts
  png) echo "set term png truecolor font \"Sans,5\" size 3200,$plot_height";;
  # pdf makes a new page for each plot :/
  pdf) echo "set term pdf color font \"Sans,5\" size $page_with,$page_height";;
  ps) echo "set term postscript portrait color solid \"Sans\" 7 size $page_with,$page_height";;
  svg) echo "set term svg size 3200, $plot_height font \"Sans,7\"";;
esac
cat <<EOF
set output '$base.$format'
# two columns, padplots and other statistics
set multiplot layout $num_padlogs,2 columnsfirst title "$title"

set lmargin 20
set rmargin 20

set pointsize 2.0

unset xlabel
unset xtics
set xrange [0:$last_ts]
set xtics format "%g"
set xtics nomirror autofreq
set ylabel "Size (bytes)"
set ytics nomirror autofreq
set y2label "Time (sec.msec)"
set y2tics nomirror autofreq
set grid
set key box

# Calculate avg
#samples(x) = \$0 > 4 ? 5 : (\$0+1)
#avg5(x) = (shift5(x), (back1+back2+back3+back4+back5)/samples(\$0))
#shift5(x) = (back5 = back4, back4 = back3, back3 = back2, back2 = back1, back1 = x)
#init(x) = (back1 = back2 = back3 = back4 = back5 = sum = 0.0)

EOF
for file in $base/pad_*.log ; do
  name=`basename $file | sed "s/^pad_//" | sed "s/.log$//" | sed "s/_/ /g"`
  #tmin=`cut "$file" -d' ' -f5 | grep -v "^$" | sort -g | head -n 1`
  #tmax=`cut "$file" -d' ' -f5 | grep -v "^$" | sort -g | tail -n 1`
  cat <<EOF
set key title "$name"
#set label "min = %f", $tmin, ", max = %f", $tmax at graph 0.05,0.1

plot \\
  '$file' using 2:3 axes x1y1 with dots smooth frequency title 'bytes', \\
  '' using 2:5 axes x1y2 with dots smooth frequency title 'scheduling'

# some failed attempts to get averages into the dot plots
#  sum = init(0), \\
#  '' using 2:(avg5((valid(\$5)==1?\$5:0.0))) axes x1y2 with lines lw 2 title "running mean", \\
#  '' using 2:(sum = sum + (valid(\$5)==1?\$5:0.0), sum/(\$0+1))axes x1y2 with lines lw 2 title "cummulative mean"
#  $tmin axes x1y2 with lines title 'min'
#  $tmax axes x1y2 with lines title 'max'
EOF
done
cat <<EOF
set y2label
unset y2tics

set size 0.5,$height1
set origin 0.5,$plt_perf_origin
set xlabel "Time (sec.msec)"
set xtics format "%g"
set ylabel "Percent"
set ytics nomirror autofreq
set yrange [0:100]
set key title "performance"
plot \\
  '$base/rusage.log' using 2:3 axes x1y1 with lines title 'cpuload', \\
  '$base/ev_qos.log' using 2:7 axes x1y1 with lines title 'qos'

set size 0.5,$height1
set origin 0.5,$plt_rusage_origin
set xlabel "Time (sec.msec)"
set xtics format "%g"
set ylabel "Context Switches"
set ytics nomirror autofreq
set yrange [0:*]
set key title "rusage"
plot \\
  '$base/rusage.log' using 2:4 axes x1y1 with lines title 'voluntary', \\
  '$base/rusage.log' using 2:5 axes x1y1 with lines title 'involuntary'

set size 0.5,$height1
set origin 0.5,$plt_memory_origin
set xlabel "Time (sec.msec)"
set xtics format "%g"
set ylabel "Memory (kb)"
set ytics nomirror autofreq
set yrange [0:*]
set key title "memory"
plot \\
  '$base/mallinfo.log' using 2:3 axes x1y1 with lines title 'non-mmapped space', \\
  '$base/mallinfo.log' using 2:4 axes x1y1 with lines title 'mmapped space', \\
  '$base/mallinfo.log' using 2:5 axes x1y1 with lines title 'total allocated space', \\
  '$base/mallinfo.log' using 2:6 axes x1y1 with lines title 'total free space'

set size 0.5,$height3
set origin 0.5,$plt_caps_origin
set xlabel "Time (sec.msec)"
set xtics format "%g"
set ylabel "Pads"
set ytics nomirror autofreq
set yrange [*:*]
set key title "caps"
plot \\
  '$base/get_caps.log' using 2:3:yticlabels(4) axes x1y1 with points title 'get', \\
  '$base/set_caps.log' using 2:3:yticlabels(4) axes x1y1 with points title 'set'

set size 0.5,$height3
set origin 0.5,$plt_ev_origin
set xlabel "Time (sec.msec)"
set xtics format "%g"
set ylabel "Pads"
set ytics nomirror autofreq
set yrange [*:*]
set key title "events"
plot \\
  '$base/ev_eos.log' using 2:3:(0):(\$5-\$3):yticlabels(4) axes x1y1 with vectors title 'eos', \\
  '$base/ev_newsegment.log' using 2:3:(0):(\$5-\$3):yticlabels(4) axes x1y1 with vectors title 'newsegment', \\
  '$base/ev_seek.log' using 2:3:(0):(\$5-\$3):yticlabels(4) axes x1y1 with vectors title 'seek', \\
  '$base/ev_tag.log' using 2:3:(0):(\$5-\$3):yticlabels(4) axes x1y1 with vectors title 'tag'

set size 0.5,$height2
set origin 0.5,$plt_msg_origin
set xlabel "Time (sec.msec)"
set xtics format "%g"
set ylabel "Elements"
set ytics nomirror autofreq
set yrange [*:*]
set key title "messages"
plot \\
  '$base/msg_async-done.log' using 2:3:yticlabels(4) axes x1y1 with points title 'async-done', \\
  '$base/msg_async-start.log' using 2:3:yticlabels(4) axes x1y1 with points title 'async-start', \\
  '$base/msg_clock-lost.log' using 2:3:yticlabels(4) axes x1y1 with points title 'clock-lost', \\
  '$base/msg_clock-provide.log' using 2:3:yticlabels(4) axes x1y1 with points title 'clock-provide', \\
  '$base/msg_duration.log' using 2:3:yticlabels(4) axes x1y1 with points title 'duration', \\
  '$base/msg_element.log' using 2:3:yticlabels(4) axes x1y1 with points title 'element', \\
  '$base/msg_eos.log' using 2:3:yticlabels(4) axes x1y1 with points title 'eos', \\
  '$base/msg_new-clock.log' using 2:3:yticlabels(4) axes x1y1 with points title 'new-clock', \\
  '$base/msg_state-changed.log' using 2:3:yticlabels(4) axes x1y1 with points title 'state-changed', \\
  '$base/msg_structure-change.log' using 2:3:yticlabels(4) axes x1y1 with points title 'structure-change', \\
  '$base/msg_tag.log' using 2:3:yticlabels(4) axes x1y1 with points title 'tag'

set size 0.5,$height2
set origin 0.5,$plt_qry_origin
set xlabel "Time (sec.msec)"
set xtics format "%g"
set ylabel "Elements"
set ytics nomirror autofreq
set yrange [*:*]
set key title "queries"
plot \\
  '$base/qry_duration.log' using 2:3:yticlabels(4) axes x1y1 with points title 'duration', \\
  '$base/qry_latency.log' using 2:3:yticlabels(4) axes x1y1 with points title 'latency', \\
  '$base/qry_position.log' using 2:3:yticlabels(4) axes x1y1 with points title 'position'

unset multiplot
EOF
