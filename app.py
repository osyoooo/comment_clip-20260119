# app.py
# ------------------------------------------------------------
# コメントクリップ（HTMLメール）ジェネレーター（Streamlit）
# - 週次で変更する箇所をフォーム入力し、HTMLを自動生成
# - コメンテーター7名のデフォルトセットを内蔵・編集可（保存なし）
# - カードに略歴（bio）を表示可能
# - モノグラムは常に正円（Outlook等でも崩れにくい）
# - 氏名の右に所属を横並び表示
# - 記事タイトルは左寄せ・号数の右から開始・上端揃え
# - 「記事を読む」は別タブ（target="_blank"）
# - NEW: 同一記事（号数＋タイトル＋リンク）の複数コメントを1枚に自動統合
# ------------------------------------------------------------

from __future__ import annotations

import re
import html
from datetime import date
from typing import List, Dict, Optional
from collections import OrderedDict

import streamlit as st
from streamlit.components.v1 import html as st_html


# =========================
# ユーティリティ
# =========================
def escape_nl2br(text: str) -> str:
    """HTMLエスケープ + 改行を <br> に変換"""
    if text is None:
        return ""
    return html.escape(text).replace("\n", "<br>")


def auto_monogram(full_name: str) -> str:
    """
    氏名からモノグラム（丸アイコンに表示する1文字）を自動抽出。
      - スペース（半角/全角）で姓・名を分解し、最初のトークンの先頭1文字
      - 分解できない場合は文字列の先頭1文字
    """
    if not full_name:
        return "名"
    tokens = re.split(r"[ \u3000]+", full_name.strip())
    if tokens and tokens[0]:
        return tokens[0][0]
    return full_name.strip()[0]


def format_delivery_date(d: date, style: str) -> str:
    """配信日の表記を生成。"""
    if style == "YMD":
        return f"📅 {d.year}年{d.month}月{d.day}日配信号"
    return f"📅 {d.month}月{d.day}日配信号"


def color_cycle(idx: int) -> str:
    """カード上部ストリップ色の既定サイクル。"""
    palette = ["#c7d2fe", "#a5b4fc"]
    return palette[idx % len(palette)]


def ensure_state(key: str, default):
    """st.session_state に key が無ければ default をセット"""
    if key not in st.session_state:
        st.session_state[key] = default


# =========================
# デフォルトのコメンテーター定義（※仮想名に置換）
# =========================
def get_default_commentators() -> List[Dict[str, object]]:
    """
    デフォルト7名。3番は要件に合わせて
      - 氏名: 匿名
      - 所属: 空文字
      - 略歴: 税理士
    として初期化。
    """
    return [
        {
            "id": 1,
            "name": "山田 恒一",
            "org": "山田税理士事務所",
            "bio": "地方税務局 訟務部門の実務担当、審理担当（資産課税）、不服審査機関の審査担当を経て、平成28年に税理士事務所を開業。令和5年6月より地域税務研究センター研究員。",
        },
        {
            "id": 2,
            "name": "佐藤 恒一",
            "org": "佐藤税理士事務所",
            "bio": "地方税務局 消費課税部門の係長補佐、課税部門 訟務担当の主任担当などを経て令和2年に税理士事務所を開業。地域間税協力団体連合会 専務理事。",
        },
        {
            "id": 3,
            "name": "匿名",
            "org": "",
            "bio": "税理士",
        },
        {
            "id": 4,
            "name": "高橋 直也",
            "org": "サンプル電子工業株式会社",
            "bio": "経理財務統括部 税務部長、理事 経理財務本部 税務部長、フェロー 経理財務本部 税務部長を経て、経理財務本部 フェロー（グローバル税務マネジメント担当）。",
        },
        {
            "id": 5,
            "name": "鈴木 正明",
            "org": "サンプル繊維株式会社",
            "bio": "理事（税務） 税務室長を経て、現在、シニアフェロー（税務会計） 財務経理部門担当。",
        },
        {
            "id": 6,
            "name": "伊藤 英雄",
            "org": "サンプル機械株式会社",
            "bio": "財務部 税務グループ長、税務部長を経て監査役室 専任監査役。",
        },
        {
            "id": 7,
            "name": "中村 有子",
            "org": "サンプルヘルスケア株式会社",
            "bio": "税理士法人での勤務を経て、複数の上場企業で副部長などの管理職として、制度会計および経理DXを主に担当。現在 サンプルヘルスケア株式会社 ファイナンスマネジメント部 企画課 課長補佐。",
        },
    ]


# =========================
# HTMLレンダリング（単一カード）
# =========================
def render_card(
    idx: int,
    issue_label: str,
    article_title: str,
    comment_text: str,
    commenter_name: str,
    commenter_org: str,
    link_url: str,
    strip_color: str,
    monogram: Optional[str] = None,
    comment_bar_color: str = "#2563eb",
    commenter_bio: str = "",
) -> str:
    """1枚のカード（記事＋単一コメント）HTMLを返す。"""
    _issue_label = escape_nl2br(issue_label)
    _article_title = escape_nl2br(article_title)
    _comment_text = escape_nl2br(comment_text)
    _commenter_name = escape_nl2br(commenter_name)
    _commenter_org = escape_nl2br(commenter_org)
    _commenter_bio = escape_nl2br(commenter_bio or "")
    _link_url = (link_url or f"#article{idx+1}").strip()
    _strip_color = strip_color or color_cycle(idx)
    _mono = (monogram or auto_monogram(commenter_name)).strip()[:1] or "名"

    bio_html = (
        f'<div style="color:#94a3b8;font:12px/1.6 Arial,\'Hiragino Kaku Gothic ProN\',Meiryo,sans-serif;'
        f'word-break:break-word;margin-top:2px;">{_commenter_bio}</div>'
        if _commenter_bio
        else ""
    )

    card_html = f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;">
      <tbody>
        <tr><td style="height:4px;background:{_strip_color};border-top-left-radius:12px;border-top-right-radius:12px;"></td></tr>

        <!-- 見出し：号数 + 記事タイトル -->
        <tr>
          <td style="padding:16px 20px 8px 20px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tbody><tr>
                <td style="text-align:left;">
                  <span style="display:inline-block;vertical-align:middle;white-space:nowrap;color:#475569;font-weight:600;font-size:13px;line-height:13px;">{_issue_label}</span>
                  <span style="display:inline-block;vertical-align:middle;margin-left:6px;color:#0f172a;font-weight:700;font-size:19px;line-height:19px;word-break:break-word;">{_article_title}</span>
                </td>
              </tr></tbody>
            </table>
          </td>
        </tr>

        <tr><td style="padding:6px 20px 0 20px;color:#64748b;font:600 13px/1 Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;">コメント</td></tr>
        <tr>
          <td style="padding:10px 20px 6px 20px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tbody><tr>
                <td style="width:6px;background:{comment_bar_color};"></td>
                <td style="padding:8px 0 8px 12px;color:#334155;font:15px/1.8 Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;">{_comment_text}</td>
              </tr></tbody>
            </table>
          </td>
        </tr>

        <tr>
          <td style="padding:2px 20px 0 20px;">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0">
              <tbody><tr>
                <td style="width:1%;vertical-align:middle;">
                  <div style="width:40px;height:40px;max-width:40px;min-width:40px;border-radius:50%;
                              background:#eef2f7;color:#64748b;
                              font:700 18px Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;
                              line-height:40px;text-align:center;">
                    {_mono}
                  </div>
                </td>
                <td style="width:12px;"></td>
                <td style="color:#0f172a;font:600 15px/1.3 Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;">
                  <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                    <tbody><tr>
                      <td style="white-space:nowrap;vertical-align:baseline;color:#0f172a;font:600 15px/1.3 Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;">{_commenter_name}</td>
                      <td style="width:10px;"></td>
                      <td style="vertical-align:baseline;color:#64748b;font:13px/1.4 Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;word-break:break-word;">{_commenter_org}</td>
                    </tr></tbody>
                  </table>
                  {bio_html}
                </td>
              </tr></tbody>
            </table>
          </td>
        </tr>

        <tr>
          <td style="padding:12px 20px 18px 20px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tbody><tr>
                <td style="background:#e8f0ff;border:1px solid #c7d2fe;border-radius:8px;">
                  <a href="{_link_url}" target="_blank" rel="noopener noreferrer"
                     style="display:block;width:100%;text-align:center;color:#1d4ed8;text-decoration:none;font:700 15px/1 Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;padding:12px 18px;border-radius:8px;">
                    記事を読む
                  </a>
                </td>
              </tr></tbody>
            </table>
          </td>
        </tr>
      </tbody>
    </table>
    """
    return card_html


# =========================
# HTMLレンダリング（複数コメントを1枚に集約）
# =========================
def render_card_grouped(
    idx: int,
    issue_label: str,
    article_title: str,
    link_url: str,
    strip_color: str,
    entries: List[Dict[str, str]],  # {comment, name, org, bio, monogram, comment_bar_color}
) -> str:
    _issue_label = escape_nl2br(issue_label)
    _article_title = escape_nl2br(article_title)
    _link_url = (link_url or f"#article{idx+1}").strip()
    _strip_color = strip_color or color_cycle(idx)

    commentators = [escape_nl2br(e.get("name", "")) for e in entries]
    monograms = [(e.get("monogram") or auto_monogram(e.get("name", "")))[:1] or "名" for e in entries]

    chips_html = "".join(
        f"""<div style="width:28px;height:28px;border-radius:50%;background:#eef2f7;color:#64748b;
                    font:700 14px/28px Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;
                    text-align:center;display:inline-block;margin-right:6px;">{m}</div>"""
        for m in monograms[:5]
    )
    more_badge = ""
    if len(monograms) > 5:
        more_badge = f"""<span style="display:inline-block;margin-left:4px;color:#475569;
                          font:600 12px/1 Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;">+{len(monograms)-5}</span>"""

    # 各コメントブロック
    comment_blocks = []
    for e in entries:
        _comment = escape_nl2br(e.get("comment", ""))
        _name = escape_nl2br(e.get("name", ""))
        _org = escape_nl2br(e.get("org", ""))
        _bio = escape_nl2br(e.get("bio", "") or "")
        _mono = (e.get("monogram") or auto_monogram(e.get("name", "")))[:1] or "名"
        bar = e.get("comment_bar_color") or "#2563eb"

        bio_html = (
            f"<div style=\"color:#94a3b8;font:12px/1.6 Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;"
            f"word-break:break-word;margin-top:2px;\">{_bio}</div>"
            if _bio
            else ""
        )

        block = f"""
        <tr><td style="padding:10px 20px 0 20px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            <tbody>
              <tr>
                <td style="width:6px;background:{bar};"></td>
                <td style="padding:10px 0 10px 12px;color:#334155;font:15px/1.8 Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;">{_comment}</td>
              </tr>
            </tbody>
          </table>
        </td></tr>

        <tr><td style="padding:2px 20px 10px 20px;">
          <table role="presentation" cellpadding="0" cellspacing="0" border="0">
            <tbody><tr>
              <td style="width:1%;vertical-align:middle;">
                <div style="width:40px;height:40px;border-radius:50%;background:#eef2f7;color:#64748b;
                            font:700 18px Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;line-height:40px;text-align:center;">
                  {_mono}
                </div>
              </td>
              <td style="width:12px;"></td>
              <td style="color:#0f172a;font:600 15px/1.3 Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;">
                <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                  <tbody><tr>
                    <td style="white-space:nowrap;vertical-align:baseline;color:#0f172a;font:600 15px/1.3 Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;">{_name}</td>
                    <td style="width:10px;"></td>
                    <td style="vertical-align:baseline;color:#64748b;font:13px/1.4 Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;word-break:break-word;">{_org}</td>
                  </tr></tbody>
                </table>
                {bio_html}
              </td>
            </tr></tbody>
          </table>
        </td></tr>
        """
        comment_blocks.append(block)

    comments_html = "\n<tr><td style=\"height:10px;\"></td></tr>\n".join(comment_blocks)

    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;">
      <tbody>
        <tr><td style="height:4px;background:{_strip_color};border-top-left-radius:12px;border-top-right-radius:12px;"></td></tr>

        <!-- 見出し（左=号数+タイトル / 右=複数コメントバッジ） -->
        <tr>
          <td style="padding:16px 20px 6px 20px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tbody><tr>
                <td style="text-align:left;">
                  <span style="display:inline-block;vertical-align:middle;white-space:nowrap;color:#475569;font-weight:600;font-size:13px;line-height:13px;">{_issue_label}</span>
                  <span style="display:inline-block;vertical-align:middle;margin-left:6px;color:#0f172a;font-weight:700;font-size:19px;line-height:19px;word-break:break-word;">{_article_title}</span>
                </td>
                <td style="text-align:right;white-space:nowrap;">
                  <span style="display:inline-block;background:#f1f5ff;border:1px solid #c7d2fe;color:#1d4ed8;font-weight:700;font-size:12px;padding:6px 10px;border-radius:14px;">
                    {len(entries)}件 / {len(set(commentators))}名
                  </span>
                </td>
              </tr></tbody>
            </table>

            <div style="margin-top:8px;">{chips_html}{more_badge}</div>
          </td>
        </tr>

        <!-- コメント群 -->
        {comments_html}

        <!-- ボタン -->
        <tr>
          <td style="padding:14px 20px 18px 20px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tbody><tr>
                <td style="background:#e8f0ff;border:1px solid #c7d2fe;border-radius:8px;">
                  <a href="{_link_url}" target="_blank" rel="noopener noreferrer"
                     style="display:block;width:100%;text-align:center;color:#1d4ed8;text-decoration:none;font:700 15px/1 Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;padding:12px 18px;border-radius:8px;">
                    記事を読む
                  </a>
                </td>
              </tr></tbody>
            </table>
          </td>
        </tr>
      </tbody>
    </table>
    """


# =========================
# 同一記事をまとめる
# =========================
def group_cards_by_article(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    """
    rows: 単票のcards_data（既存構造）
    return: [{issue, title, link, strip_color, entries:[...] }] の配列（順序保持）
    """
    buckets: "OrderedDict[tuple, Dict[str, object]]" = OrderedDict()
    for r in rows:
        key = (r.get("issue", "").strip(), r.get("title", "").strip(), r.get("link", "").strip())
        if key not in buckets:
            buckets[key] = {
                "issue": r.get("issue", "").strip(),
                "title": r.get("title", "").strip(),
                "link": r.get("link", "").strip(),
                "strip_color": r.get("strip_color") or "#c7d2fe",
                "entries": [],
            }
        buckets[key]["entries"].append(
            {
                "comment": r.get("comment", ""),
                "name": r.get("name", ""),
                "org": r.get("org", ""),
                "bio": r.get("bio", ""),
                "monogram": r.get("monogram", ""),
                "comment_bar_color": r.get("comment_bar_color", "#2563eb"),
            }
        )
        if not buckets[key]["strip_color"]:
            buckets[key]["strip_color"] = r.get("strip_color") or color_cycle(0)
    return list(buckets.values())


# =========================
# メール全体レンダリング
# =========================
def render_email_full(
    title_text: str,
    badge_text: str,
    header_title: str,
    delivery_text: str,
    description_text: str,
    cards: List[str],
) -> str:
    _title_text = escape_nl2br(title_text)
    _badge_text = escape_nl2br(badge_text)
    _header_title = escape_nl2br(header_title)
    _delivery_text = escape_nl2br(delivery_text)
    _description_text = escape_nl2br(description_text)

    spacer = '<div style="height:18px;line-height:18px;">&nbsp;</div>'
    body_cards_html = spacer.join(cards)

    html_full = f"""<meta charset="UTF-8">
<title>{_title_text}</title>

<!-- 100% wrapper -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0;padding:0;background:#f3f6fb;">
  <tbody><tr>
    <td align="center" style="padding:0;">

      <!-- ===== Header ===== -->
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#0b1b34;">
        <tbody><tr>
          <td align="center" style="padding:0;">
            <table role="presentation" width="900" cellpadding="0" cellspacing="0" border="0" style="max-width:900px;width:100%;">
              <tbody><tr>
                <td style="padding:20px 24px 12px 24px;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tbody><tr>
                      <td>
                        <span style="display:inline-block;vertical-align:middle;background:#22315b;border:1px solid #2f3c66;color:#ffffff;font-weight:800;font-size:12px;letter-spacing:.04em;padding:7px 14px;border-radius:16px;font-family:Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;">{_badge_text}</span>
                        <span style="display:inline-block;vertical-align:middle;margin-left:12px;color:#ffffff;font-weight:800;font-size:22px;letter-spacing:.01em;font-family:Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;">{_header_title}</span>
                      </td>
                    </tr></tbody>
                  </table>
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tbody><tr>
                      <td style="padding-top:8px;color:#dbeafe;font-size:14px;font-family:Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;">{_delivery_text}</td>
                    </tr></tbody>
                  </table>
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tbody><tr>
                      <td style="padding-top:6px;color:#c7d2fe;font-size:13px;line-height:1.7;font-family:Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;">
                        {_description_text}
                      </td>
                    </tr></tbody>
                  </table>
                </td>
              </tr></tbody>
            </table>
          </td>
        </tr></tbody>
      </table>
      <!-- ===== /Header ===== -->

      <!-- ===== Body ===== -->
      <table role="presentation" width="900" cellpadding="0" cellspacing="0" border="0" style="max-width:900px;width:100%;background:#f3f6fb;">
        <tbody><tr>
          <td style="padding:24px;">
            {body_cards_html}
          </td>
        </tr></tbody>
      </table>
      <!-- ===== /Body ===== -->

      <!-- ===== Footer ===== -->
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#0b1b34;">
        <tbody><tr>
          <td align="center" style="padding:18px 12px;">
            <div style="color:#ffffff;font:12.5px/1.6 Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;">
              Copyright© 2016 Sample Publishing Group, All rights reserved.
            </div>
            <div style="margin-top:8px;font-family:Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;">
              <a href="https://www.example.com/privacy/" style="color:#ffffff;text-decoration:none;margin:0 10px;">個人情報の保護について</a>
              <a href="https://www.example.com/contact/" style="color:#ffffff;text-decoration:none;margin:0 10px;">お問い合わせ</a>
            </div>
          </td>
        </tr></tbody>
      </table>
      <!-- ===== /Footer ===== -->

    </td>
  </tr></tbody>
</table>
"""
    return html_full


# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="コメントクリップ HTMLメーカー", layout="wide")

st.title("コメントクリップ（HTMLメール）メーカー")
st.caption("週次の入力内容をフォームで設定 → HTMLを生成・プレビュー・ダウンロード")

# コメンテーター：セッション初期化
DEFAULT_COMMENTATORS = get_default_commentators()
for i, c in enumerate(DEFAULT_COMMENTATORS):
    ensure_state(f"cmt_name_{i}", c["name"])
    ensure_state(f"cmt_org_{i}", c["org"])
    ensure_state(f"cmt_bio_{i}", c["bio"])
    ensure_state(f"cmt_mono_{i}", auto_monogram(c["name"]))

with st.sidebar:
    st.header("入力方法")
    input_mode = st.radio(
        "カードの入力方法を選択",
        options=("フォームで入力", "CSVをアップロード"),
        index=0,
    )
    st.markdown("---")
    st.subheader("CSV仕様（任意）")
    st.markdown(
        """
**列名（ヘッダ必須）**  
- `issue` / `title` / `comment` / `name` / `org` / `link`  
**任意列**  
- `monogram`  
- `strip_color`  
- `commentator`（1〜7 または氏名で、設定中のコメンテーターから補完）  
- `bio`（略歴）
        """.strip()
    )

    example_csv = (
        "issue,title,comment,name,org,link,monogram,strip_color\n"
        "第3742号,（記事タイトル例）,💬 コメント例,田中 太郎,田中税理士事務所,#article1,,#c7d2fe\n"
        "第3743号,（記事タイトル例）,💬 コメント例,佐藤 花子,サンプル商事 経理部,#article2,,#a5b4fc\n"
    ).encode("utf-8")
    st.download_button(
        "CSV雛形をダウンロード",
        data=example_csv,
        file_name="comments_template.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ① 基本設定（ヘッダ）
st.subheader("① 基本設定（ヘッダ）")
c1, c2, c3 = st.columns([1.2, 1.2, 1.0])

with c1:
    title_text = st.text_input(
        "メールの<title>（ブラウザ表示用）",
        value="コメントクリップ（メール配信用・全幅ヘッダー＆横長ボタン）",
    )
    badge_text = st.text_input("バッジ名", value="COMMENT CLIP")
with c2:
    header_title = st.text_input("ヘッダーの大見出し", value="週刊 サンプル専門誌")
    delivery_style = st.radio(
        "配信日の表記",
        options=("月日（例: 9月1日配信号）", "年月日（例: 2025年9月1日配信号）"),
        index=0,
    )
with c3:
    delivery_date = st.date_input("配信日", value=date.today())
    description_text = st.text_area(
        "説明文",
        value=(
            "多様な視点からのコメントが記事を読むきっかけとなり、普段触れない分野への関心を広げます。"
            "また、コメントが「後々の記事の読み返し」を促す機能を果たすので、記憶の定着の向上も目的の一つです。"
            "※サンプルデータベースをご利用の方は、ログイン後に『記事を読む』を押下いただくと該当記事へ遷移いたします。"
            "※本メール内のコメントはコメンテーターの私見です"
        ),
        height=96,
    )

delivery_text = format_delivery_date(delivery_date, "MD" if delivery_style.startswith("月日") else "YMD")

# ② コメンテーター設定
st.subheader("② コメンテーター設定（このセッション内で編集可・保存なし）")
st.caption("全コメンテーターがカード側のプルダウンに表示されます。ここでモノグラムも設定できます（1文字推奨）。")

cols = st.columns(2)
for i, base in enumerate(get_default_commentators()):
    with cols[i % 2]:
        with st.expander(
            f"{i+1}. {st.session_state[f'cmt_name_{i}']} / {st.session_state[f'cmt_org_{i}'] or '（所属未設定）'}",
            expanded=(i < 2),
        ):
            st.text_input("氏名", key=f"cmt_name_{i}")
            st.text_input("所属（空欄可）", key=f"cmt_org_{i}")
            st.text_area("略歴（任意）", key=f"cmt_bio_{i}", height=80)
            st.text_input("モノグラム（1文字推奨・未入力時は氏名から自動）", key=f"cmt_mono_{i}")

ALL_COMMENTATORS: List[Dict[str, str]] = []
for i, base in enumerate(get_default_commentators()):
    name_i = st.session_state[f"cmt_name_{i}"].strip()
    org_i = st.session_state[f"cmt_org_{i}"].strip()
    bio_i = st.session_state[f"cmt_bio_{i}"].strip()
    mono_raw = (st.session_state.get(f"cmt_mono_{i}", "") or "").strip()
    mono_i = (mono_raw[:1] or auto_monogram(name_i))
    ALL_COMMENTATORS.append(
        {
            "id": base["id"],
            "name": name_i,
            "org": org_i,
            "bio": bio_i,
            "mono": mono_i,
        }
    )

# ③ カード設定（記事＋コメント）
st.subheader("③ カード設定（記事＋コメント）")

cards_data: List[Dict[str, str]] = []

if input_mode == "CSVをアップロード":
    uploaded = st.file_uploader("CSVをアップロード", type=["csv"])
    if uploaded is not None:
        import pandas as pd

        try:
            df = pd.read_csv(uploaded)
            required_cols = {"issue", "title", "comment", "name", "org", "link"}
            if not required_cols.issubset(df.columns):
                st.error(f"CSVに必要な列が不足しています: {sorted(required_cols)}")
            else:
                for i, row in df.iterrows():
                    commentator_token = str(row.get("commentator", "")).strip()
                    cmt_from_token = None
                    if commentator_token:
                        try:
                            token_id = int(float(commentator_token))
                            cmt_from_token = next((c for c in ALL_COMMENTATORS if c["id"] == token_id), None)
                        except Exception:
                            cmt_from_token = next((c for c in ALL_COMMENTATORS if c["name"] == commentator_token), None)

                    name_val = str(row.get("name", "")).strip()
                    org_val = str(row.get("org", "")).strip()
                    bio_val = str(row.get("bio", "")).strip()
                    mono_val = str(row.get("monogram", "")).strip()

                    if cmt_from_token:
                        if not name_val:
                            name_val = cmt_from_token["name"]
                        if not org_val:
                            org_val = cmt_from_token["org"]
                        if not bio_val:
                            bio_val = cmt_from_token.get("bio", "")
                        if not mono_val:
                            mono_val = cmt_from_token.get("mono", "")

                    mono_val = (mono_val[:1] or auto_monogram(name_val))

                    cards_data.append(
                        {
                            "issue": str(row.get("issue", "")).strip(),
                            "title": str(row.get("title", "")).strip(),
                            "comment": str(row.get("comment", "")).strip(),
                            "name": name_val,
                            "org": org_val,
                            "bio": bio_val,
                            "link": str(row.get("link", f"#article{i+1}")).strip(),
                            "monogram": mono_val,
                            "strip_color": str(row.get("strip_color", "")).strip(),
                        }
                    )
                st.success(f"{len(cards_data)} 件のカードを読み込みました。右側でプレビュー可能です。")
        except Exception as e:
            st.error(f"CSVの読み込みに失敗しました: {e}")

else:
    # フォーム入力
    comment_bar_color = st.color_picker("コメント左バー（既定）は #2563eb", value="#2563eb", key="bar")
    num_cards = st.number_input("カード数（コメント行の数）", min_value=1, max_value=40, value=7, step=1)

    def _label(c): return f"{c['name']}（{c['org'] or '所属未設定'}）"
    cmt_options = ["-- 手動入力 --"] + [_label(c) for c in ALL_COMMENTATORS]

    for i in range(int(num_cards)):
        with st.expander(f"カード（コメント行） {i+1}", expanded=(i == 0)):
            col1, col2 = st.columns([1.0, 1.0])

            with col1:
                st.text_input("号数（例: 第3742号）", key=f"issue_{i}", value=f"第{3742+i}号")
                st.text_input("記事タイトル", key=f"title_{i}", value="")
                strip_color = st.color_picker("カード上部ストリップ色（同一記事で最初の行が採用）", value=color_cycle(i), key=f"strip_{i}")

            with col2:
                default_index = (i % len(ALL_COMMENTATORS)) + 1
                selected_label = st.selectbox(
                    "コメンテーター（選ぶと下へ反映／手動編集可）",
                    options=cmt_options,
                    index=min(default_index, len(cmt_options) - 1),
                    key=f"cmt_select_{i}",
                )
                selected_cmt = None
                if selected_label != cmt_options[0]:
                    sel_idx = cmt_options.index(selected_label) - 1
                    selected_cmt = ALL_COMMENTATORS[sel_idx]

                name_key, org_key, bio_key, mono_key = f"name_{i}", f"org_{i}", f"bio_{i}", f"mono_{i}"

                if selected_cmt:
                    if not st.session_state.get(name_key, ""):
                        st.session_state[name_key] = selected_cmt["name"]
                    if not st.session_state.get(org_key, ""):
                        st.session_state[org_key] = selected_cmt["org"]
                    if not st.session_state.get(bio_key, ""):
                        st.session_state[bio_key] = selected_cmt.get("bio", "")
                    if not st.session_state.get(mono_key, ""):
                        st.session_state[mono_key] = selected_cmt.get("mono", "") or auto_monogram(selected_cmt["name"])

                if st.button("↑ 選択の内容で氏名・所属・略歴・モノグラムを上書き", key=f"apply_{i}") and selected_cmt:
                    st.session_state[name_key] = selected_cmt["name"]
                    st.session_state[org_key] = selected_cmt["org"]
                    st.session_state[bio_key] = selected_cmt.get("bio", "")
                    st.session_state[mono_key] = selected_cmt.get("mono", "") or auto_monogram(selected_cmt["name"])

                st.text_input("氏名（例: 田中 太郎）", key=name_key)
                st.text_input("所属（空欄可）", key=org_key)
                st.text_area("略歴（カードに表示・任意）", key=bio_key, height=72)
                st.text_input("モノグラム（任意・1文字推奨）", key=mono_key)
                st.text_input("ボタンのリンク（#articleX または URL）", key=f"link_{i}", value=f"#article{i+1}")

            st.text_area("コメント本文（複数行OK）", key=f"comment_{i}", value="💬 ")

            mono_final = (st.session_state.get(f"mono_{i}", "") or auto_monogram(st.session_state.get(f"name_{i}", "")))[:1]

            cards_data.append(
                {
                    "issue": st.session_state.get(f"issue_{i}", ""),
                    "title": st.session_state.get(f"title_{i}", ""),
                    "comment": st.session_state.get(f"comment_{i}", ""),
                    "name": st.session_state.get(f"name_{i}", ""),
                    "org": st.session_state.get(f"org_{i}", ""),
                    "bio": st.session_state.get(f"bio_{i}", ""),
                    "link": st.session_state.get(f"link_{i}", f"#article{i+1}"),
                    "monogram": mono_final,
                    "strip_color": strip_color,
                    "comment_bar_color": comment_bar_color,
                }
            )

# ④ 生成・プレビュー・ダウンロード
st.subheader("④ 生成・プレビュー・ダウンロード")

# NEW: まとめ表示の切替（デフォルトON）
st.caption("※ 同一記事（号数＋タイトル＋リンク）が複数行ある場合、1枚のカードに自動でまとめられます。")
use_grouping = st.checkbox("同一記事を1枚にまとめる", value=True)

# カードHTMLを構築
cards_html_list: List[str] = []
if use_grouping:
    grouped = group_cards_by_article(cards_data)
    for idx, g in enumerate(grouped):
        cards_html_list.append(
            render_card_grouped(
                idx=idx,
                issue_label=g["issue"],
                article_title=g["title"],
                link_url=g["link"],
                strip_color=g["strip_color"],
                entries=g["entries"],
            )
        )
else:
    for idx, c in enumerate(cards_data):
        cards_html_list.append(
            render_card(
                idx=idx,
                issue_label=c.get("issue", ""),
                article_title=c.get("title", ""),
                comment_text=c.get("comment", ""),
                commenter_name=c.get("name", ""),
                commenter_org=c.get("org", ""),
                link_url=c.get("link", f"#article{idx+1}"),
                strip_color=c.get("strip_color") or color_cycle(idx),
                monogram=c.get("monogram", ""),
                comment_bar_color=c.get("comment_bar_color", "#2563eb"),
                commenter_bio=c.get("bio", ""),
            )
        )

# 全体HTML
full_html = render_email_full(
    title_text=title_text,
    badge_text=badge_text,
    header_title=header_title,
    delivery_text=delivery_text,
    description_text=description_text,
    cards=cards_html_list if cards_html_list else ["<!-- No cards -->"],
)

# 2カラム：左=ソース/ダウンロード、右=プレビュー
lc, rc = st.columns([1.0, 1.1])

with lc:
    st.markdown("**生成されたHTML（コピー用）**")
    st.text_area("HTMLソース", value=full_html, height=420, label_visibility="collapsed")

    fname = f"comment_clip_{delivery_date.strftime('%Y%m%d')}.html"
    st.download_button(
        "HTMLファイルをダウンロード",
        data=full_html.encode("utf-8"),
        file_name=fname,
        mime="text/html",
        use_container_width=True,
    )

with rc:
    st.markdown("**プレビュー（ブラウザ描画）**")
    # まとめるとカード1枚の高さが上がるのでやや多めに確保
    preview_height = 520 + max(0, len(cards_html_list)) * 320
    try:
        st_html(full_html, height=min(max(preview_height, 600), 2400), scrolling=True)
    except Exception:
        st.info("プレビュー表示に失敗しましたが、HTML自体はダウンロードできます。")

st.markdown("---")
with st.expander("使い方メモ", expanded=False):
    st.markdown(
        """
1. **基本設定**でバッジ名・ヘッダー・配信日・説明文を入力します。  
2. **コメンテーター設定**で氏名・所属・略歴・モノグラムを編集します。  
3. **カード設定**で、同じ記事（号数＋タイトル＋リンク）のコメント行を複数作成すると、④で**1枚に自動統合**されます。  
4. 右側でプレビューを確認し、**HTMLファイルをダウンロード**してください。  
        """.strip()
    )
