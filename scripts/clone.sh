#!/bin/bash
set -x
repo=best-practice
if [ ! -d $repo ];then
   git clone https://gitlab.daocloud.cn/ndx/engineering/infrastructure/${repo}.git
else
   pushd $repo
   git stash
   git fetch
   git rebase origin/main
   popd
fi
yes| cp $repo/*.md .
