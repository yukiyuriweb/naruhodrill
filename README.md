# なるほドリル

考えて、なるほど。小学3年生向けの、考える力を育てる算数・国語の問題集です。

- サイト: https://naruhodrill.yukiyuriweb.com/
- 運営: YUKiYURi WEB

ログインはなく、解いた記録は使う人のブラウザ（IndexedDB）にだけ保存します。サーバーにも外部のサービスにもデータを送りません。

## 問題のまちがいを見つけたら

[Issue](https://github.com/yukiyuriweb/naruhodrill/issues) で教えてください。

## 構成

- `site/` … 静的サイト（HTML・CSS・JS）と問題データ（`site/data/<教科>/NNN.json`）
- `site/tools/build.py` … 問題の検算・形式チェックと、公開する問題だけを `dist/` に書き出す処理
- `.githooks/pre-push` … `main` を push すると、検算して `site/tools/deploy.sh` で公開する
- `site/tools/merge.sh` … PR を squash でマージして、そのまま公開する（`sh site/tools/merge.sh <PR番号>`）。GitHub の画面からマージすると公開されないので、マージはこれで行う
- `site/tools/deploy.sh.sample` … `deploy.sh` の見本。コピーして送り先（`DEST`）を書き換えて使う（`deploy.sh` はサーバーの情報を含むので git に入れない）

```sh
git config core.hooksPath .githooks   # 最初に一度だけ
cp site/tools/deploy.sh.sample site/tools/deploy.sh   # 最初に一度だけ。DEST を書き換える
uv run site/tools/build.py            # 検算と index.json の作成（下書きも含む）
python3 -m http.server 8002 --directory site   # ローカルで確認（http://localhost:8002/）
```

問題の `status` が `published` のものだけが公開されます。
