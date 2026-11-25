#!/usr/bin/env python3
"""Generate a fio job; does not access or alter any device."""
import argparse
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('fs', choices=['zonefs', 'f2fs'])
p.add_argument('workers', type=int, choices=[1, 2, 4, 8])
p.add_argument('--mount', type=Path)
a = p.parse_args()
mount = a.mount or Path('/mnt') / a.fs
print('[global]\nioengine=libaio\niodepth=1\nrw=write\nbs=64k\ndirect=1\nfile_append=1\n'
      f'size={32 // a.workers}m\nfallocate=none\ngroup_reporting=1')
if a.fs == 'zonefs':
    print('allow_file_create=0')
for i in range(a.workers):
    name = mount / 'seq' / str(i) if a.fs == 'zonefs' else mount / f'worker.{i}'
    print(f'\n[w{i}]\nfilename={name}')
