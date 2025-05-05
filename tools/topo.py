import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import polib

parser = argparse.ArgumentParser()
parser.add_argument("folder", type=Path)


def pddf2po(
    data: pd.DataFrame,
    locale: str = "ja_JP",
    col_id: str = "text_EN",
    col_str: str = "text_JP",
    col_comments: str = "text_CZ",
    col_context: str = "id",
    col_locations: Optional[str] = None,
):
    """
    Arguments
    ------
    data: must be unique in id col.
    """
    pof = initializePOFile(lang=locale)

    def format_arg(dic: dict) -> dict:
        dic["msgid"] = dic[col_id]
        dic["msgstr"] = dic[col_str]
        dic["occurrences"] = [(dic.get(col_locations), 0)]
        dic["tcomment"] = str(
            dic.get(col_comments, "")
        )  # 型の制約があるならそう書いてほしい
        dic["msgctxt"] = dic.get(col_context)
        return dic

    d = [format_arg(dict(r)) for _, r in data.iterrows()]
    keys = {"msgid", "msgstr", "flags"}
    if col_comments is not None:
        keys.add("tcomment")
    if col_context is not None:
        keys.add("msgctxt")
    if col_locations is not None:
        keys.add("occurrences")
    current_keys = list(d[0].keys())
    _ = [dic.pop(k, None) for dic in d for k in current_keys if k not in keys]
    for r in d:
        pof.append(polib.POEntry(**r))
    return pof


def initializePOFile(
    lang: str, encoding: str = "utf-8", email: Optional[str] = None
) -> polib.POFile:
    po = polib.POFile(encoding=encoding)
    dt = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S%z")
    metadata = {
        "Project-Id-Version": "1.0",
        "POT-Creation-Date": dt,
        "PO-Revision-Date": dt,
        "MIME-Version": "1.0",
        "Language": lang,
        "Content-Type": "text/plain; charset=utf-8",
        "Plural-Forms": "nplurals=1; plural=0;",
        "Genereted-BY": "polib",
        "Content-Transfer-Encoding": "8bit",
    }
    if email:
        metadata["Last-Translator"] = email
        metadata["Report-Msgid-Bugs-To"] = email
        metadata["Language-Team"] = f"""{lang}, {email}"""
    po.metadata = metadata
    return po


def main(args):
    fp_in = Path(f"{args.folder}/private/intermediate/text-codex.csv")
    fp_out = Path(f"{args.folder}/private/intermediate/codex.po")
    print(f"""reading {fp_in}""")
    d = pd.read_csv(fp_in)
    pof = pddf2po(d)
    print(f"""writing to {fp_out}""")
    pof.save(fp_out)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args)
