#!/bin/sh
# PR を squash でマージして、そのまま naruhodrill.yukiyuriweb.com に公開する。
#
# 使い方:
#   sh site/tools/merge.sh 12     # PR #12 をマージして公開
#
# GitHub の画面からマージすると公開されないので、マージはこのスクリプトで行う。
# 公開は main の最新（GitHub と同じ内容）を検算してから deploy.sh で送る。
set -eu
cd "$(dirname "$0")/../.."

if [ $# -ne 1 ]; then
  echo "使い方: sh site/tools/merge.sh <PR番号>" >&2
  exit 1
fi
# 作業中の変更が公開に混ざらないよう、未コミットの変更があるときは止める
if [ -n "$(git status --porcelain)" ]; then
  echo "merge.sh: コミットしていない変更があります。コミットするか退避してから実行してください。" >&2
  exit 1
fi
if [ ! -f site/tools/deploy.sh ]; then
  echo "merge.sh: site/tools/deploy.sh がありません。deploy.sh.sample をコピーして、送り先（DEST）を書き換えてください。" >&2
  exit 1
fi

gh pr merge "$1" --squash
git checkout main
git pull --ff-only origin main
echo "merge.sh: main（$(git log --oneline -1)）を公開します" >&2
sh site/tools/deploy.sh
