#ifndef fooifacepfroutehfoo
#define fooifacepfroutehfoo

/* $Id: iface-pfroute.h 957 2005-11-13 17:44:10Z lennart $ */

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
#include <avahi-common/watch.h>

typedef struct AvahiPfRoute AvahiPfRoute;
struct AvahiPfRoute {
  int fd;
  AvahiWatch *watch;
  AvahiInterfaceMonitor *m;
};

typedef struct AvahiInterfaceMonitorOSDep AvahiInterfaceMonitorOSDep;

struct AvahiInterfaceMonitorOSDep {
    AvahiPfRoute *pfroute;
};

#endif
