#!/usr/bin/python3

import sys,os,glob
import subprocess as sp
from pathlib import Path
import utils 
import shutil

if len(sys.argv) < 4:
  print("usage : {} <target> <input.bc> <output_dir> <compile args ...>")
  exit(0)

target_loc = sys.argv[1]
bc_fn = sys.argv[2]
output_dir = sys.argv[3]
compile_argvs = sys.argv[4:]

if not utils.check_given_bitcode(bc_fn):
  exit(1)

shutil.rmtree("tmpdir", ignore_errors=True)
os.mkdir("tmpdir")

with open("tmpdir/BBtargets.txt", "w") as f1:
  f1.write(target_loc)

orig_filename = ".".join(bc_fn.split(".")[:-1])

cmd = ["ldd", orig_filename]

out = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE).stdout.decode()

skip_list = [
  "libc.so", "linux-vdso.so", "libgcc_s.so", "ld-linux-x86-64.so", "libuuid",
  "libdbus-1.so", "libsystemd.so", "libwrap.so",
  "libsndfile.so", "libasyncns.so", "libapparmor.so", "liblz4.so", "libgcrypt.so",
  "libFLAC.so", "libogg.so", "libvorbis.so", "libvorbisenc.so", "libgpg-error.so",
  "libpulsecommon"
]

link_commands = []
is_cxx = False
for line in out.split("\n"):
  skip = False
  for skip_lib in skip_list:
    if skip_lib in line:
      skip = True
      break
  
  if skip:
    continue

  if "libstdc++" in line:
    is_cxx = True
    continue

  if "=>" not in line:
    continue

  line = line.strip().split("=>")[0]

  if "lib" not in line and "so" not in line:
    continue

  while "  " in line:
    line = line.replace("  ", " ")
  
  line = line.split("lib")[1].split(".so")[0]
  
  link_commands.append("-l" + line)

source_file_path = Path(__file__).resolve()
aflgo_dir = str(source_file_path.parent.parent)

if is_cxx:
  cmd_0 = ["{}/afl-clang-fast++".format(aflgo_dir)]
else:
  cmd_0 = ["{}/afl-clang-fast".format(aflgo_dir)]

cmd = cmd_0 + [bc_fn, "-o", "{}.tmp".format(orig_filename)] + \
  ["-targets=tmpdir/BBtargets.txt", "-outdir=tmpdir", "-flto", "-fuse-ld=gold",
   "-Wl,-plugin-opt=save-temps"] + link_commands + compile_argvs

print(" ".join(cmd))
runres = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)

cmd = ["python3", "{}/scripts/gen_distance_fast.py".format(aflgo_dir), os.getcwd(), os.getcwd()+"/tmpdir", orig_filename]
print(" ".join(cmd))
sp.run(cmd)

cmd = cmd_0 + [bc_fn, "-o", "{}/{}.afl".format(output_dir, orig_filename) ] + \
  [ "-distance=tmpdir/distance.cfg.txt" ] + link_commands + compile_argvs
print(" ".join(cmd))
sp.run(cmd)
