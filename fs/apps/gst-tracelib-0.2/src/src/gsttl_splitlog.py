#!/usr/bin/python
# gsttl_splitlog.py <logfile>
#
# splits logfile into separate logs per type
# takes basename from log and creates subdir with splitted logs
# it takes the first field from each logline as the key
# does not remove anything if directory already exists

import sys, os, os.path

def cmp_ts(s1, s2):
  (tm1,ts1,data1)=s1.partition(' ');
  (tm2,ts2,data2)=s2.partition(' ');
  return s1 < s2

def main():
  # parse args
  if len(sys.argv) > 1:
    file_name=sys.argv[1]
  else:
    file_name='gsttl.log'
    
  # get directory name and create dir for results
  (dir_name,ext)=os.path.splitext(file_name)
  if not os.path.exists(dir_name):
    os.mkdir(dir_name)
  
  try:
    f=open(file_name, 'r')
  except IOError, e:              # catch IOErrors, e is the instance
    print "Can't open file %s: " % file_name, e # print exception info if thrown
    exit(1);
  
  # iterate over log and split
  fds = {};
  for line in f:
    (key,sep,data)=line.partition(' ');
  
    fd=fds.get(key)
    if fd == None:
      fd=open("%s/%s.log" % (dir_name,key), 'w')
      fds[key]=fd
  
    # hack to ensure locale independent float format
    data=str.replace(data, ",", ".")
    fd.write(data)
  
  print "splitted %s into %d separate logs under %s" % (file_name, len(fds), dir_name)
  # close all files
  f.close()
  for fd in fds.values():
    fd.close()
  
  for key in fds.keys():
    f=open("%s/%s.log" % (dir_name,key), 'r')
    lines = []
    for line in f:
      lines.append(line)
    f.close()
    #os.rename("%s/%s.log" % (dir_name,key), "%s/%s.log.bak" % (dir_name,key))
    lines.sort(cmp_ts)
    f=open("%s/%s.log" % (dir_name,key), 'w')
    for line in lines:
      f.write(line)
    f.close();
  
  print "sorted all logs by timestamp"

if __name__ == '__main__':
  main()
