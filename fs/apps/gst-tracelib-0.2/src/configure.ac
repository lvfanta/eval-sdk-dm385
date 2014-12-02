#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_INIT([gst-tracelib], [0.2], [ensonic@users.sf.net])
AC_CONFIG_SRCDIR([ChangeLog])
AC_CONFIG_HEADER([config.h])

dnl Initialise the automake tool
AM_INIT_AUTOMAKE([check-news])

# Checks for programs.
AC_PROG_CC
AC_PROG_INSTALL
AC_PROG_LIBTOOL
PKG_PROG_PKG_CONFIG

# Checks for libraries.
# FIXME: Replace `main' with a function in `-lrt':
AC_CHECK_LIB([rt], [main])

# Checks for header files.
AC_HEADER_STDC
AC_CHECK_HEADERS([malloc.h stdlib.h string.h sys/time.h sys/resource.h unistd.h])

# Checks for typedefs, structures, and compiler characteristics.
AC_C_CONST

# Checks for library functions.
AC_FUNC_VPRINTF
AC_CHECK_FUNCS([clock_gettime getrusage mallinfo strerror])

dnl Checks for libraries.
PKG_CHECK_MODULES(BASE_DEPS, \
  glib-2.0 >= 2.2.0 gstreamer-0.10 >= 0.10.0 \
)
AC_SUBST(BASE_DEPS_LIBS)
AC_SUBST(BASE_DEPS_CFLAGS)

AC_CONFIG_FILES(
  Makefile \
  src/Makefile \
  src/gsttl \
)
AC_OUTPUT
