#ifndef fooprioqhfoo
#define fooprioqhfoo

/* $Id: prioq.h 308 2005-08-13 21:25:09Z lennart $ */

/***
  This file is part of avahi.
 
  avahi is free software; you can redistribute it and/or modify it
  under the terms of the GNU Lesser General Public License as
  published by the Free Software Foundation; either version 2.1 of the
  License, or (at your option) any later version.
 
  avahi is distributed in the hope that it will be useful, but WITHOUT
  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
  or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
  Public License for more details.
 
  You should have received a copy of the GNU Lesser General Public
  License along with avahi; if not, write to the Free Software
  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
  USA.
***/

typedef struct AvahiPrioQueue AvahiPrioQueue;
typedef struct AvahiPrioQueueNode AvahiPrioQueueNode;

typedef int (*AvahiPQCompareFunc)(const void* a, const void* b);

struct AvahiPrioQueue {
    AvahiPrioQueueNode *root, *last;
    unsigned n_nodes;
    AvahiPQCompareFunc compare;
};

struct AvahiPrioQueueNode {
    AvahiPrioQueue *queue;
    void* data;
    unsigned x, y;
    AvahiPrioQueueNode *left, *right, *parent, *next, *prev;
};

AvahiPrioQueue* avahi_prio_queue_new(AvahiPQCompareFunc compare);
void avahi_prio_queue_free(AvahiPrioQueue *q);

AvahiPrioQueueNode* avahi_prio_queue_put(AvahiPrioQueue *q, void* data);
void avahi_prio_queue_remove(AvahiPrioQueue *q, AvahiPrioQueueNode *n);

void avahi_prio_queue_shuffle(AvahiPrioQueue *q, AvahiPrioQueueNode *n);

#endif
