#!/bin/sh
#
# basic autogen script for autofoo
#

# a silly hack that generates autoregen.sh but it's handy
echo "#!/bin/sh" > autoregen.sh
echo "./autogen.sh $@ \$@" >> autoregen.sh
chmod +x autoregen.sh

# bootstarp
set -x
libtoolize --automake --copy
aclocal
autoconf
autoheader
automake --add-missing --foreign --copy
./configure "$*"

