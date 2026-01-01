#! /usr/bin/env python3

import argparse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
import regex
from module.params import parser, rename_args

OUTFILE: List[Tuple[str, str]] = [
    (
        r"^ui_codex_",
        "codex",
    ),
    (
        r"^ui_nm_",
        "ui_name",
    ),
    (
        r"^ui_",
        "ui",
    ),
]


@dataclass
class TranslationDicts:
    by_id: pd.DataFrame
    by_match: pd.DataFrame
    rev_by_match: pd.DataFrame


def read_xml(filepath: Path) -> pd.DataFrame:
    print(f"reading {filepath.name}")
    xml = ET.parse(filepath)
    root = xml.getroot()
    d = pd.DataFrame(
        [[cell.text for cell in row.findall("Cell")] for row in root.findall("Row")],
        columns=["id", "text1", "text2"],
    ).assign(fp=filepath.name)
    return d


def read_xmls(dirpath: Path):
    ds = []
    for fp in dirpath.glob("*.xml"):
        d = read_xml(fp)
        ds += [d]
    return pd.concat(ds)


def df_2_xml(data: pd.DataFrame) -> ET:
    xml = ET.fromstring("<Table></Table>")
    xml = ET.ElementTree(xml)
    root = xml.getroot()
    for _, r in data.iterrows():
        try:
            string = f"<Row><Cell>{str(r["id"])}</Cell><Cell>{str(r["text_EN"])}</Cell><Cell>{str(r["text"])}</Cell></Row>"
            entry = ET.fromstring(string)
        except Exception as e:
            raise ValueError(f"""error occured at `{r["id"]}`, string={string}: {e}""")
        root.append(entry)
    ET.indent(xml, space="  ", level=0)
    return xml


def replace_text_regex(text_series: pd.Series, dictionary: pd.DataFrame) -> List[str]:
    """
    Args
    ------
    dictionary
        text, modified 列を持つpd.DataFrame
    """

    def replace(text_list: List[str], match: str, replace: str) -> List[str]:
        pat = regex.compile(r"([^\p{katakana}ー])" + match + r"([^\p{katakana}ー])")
        s = [pat.sub(str(x), f"""\1{replace}\2""") for x in text_list]
        pat2 = regex.compile(r"(\s)" + match + r"([^\p{katakana}ー])")
        s = [pat2.sub(str(x), r"\1" + f"""{replace}\2""") for x in s]
        pat3 = regex.compile(r"^" + match + r"([^\p{katakana}ー])")
        s = [pat3.sub(str(x), f"""{replace}\1""") for x in s]
        return s

    text_series = text_series.values.tolist()
    for _, r in dictionary.iterrows():
        text_series = replace(text_series, str(r["text"]), str(r["modified"]))
    return text_series


def escape_xml_symbols(
    data: pd.DataFrame, col_text_en: str = "text_EN", col_text: str = "text"
) -> pd.DataFrame:
    """
    XMLのテキストとしてエスケープが必要なものを置換する
    """
    # ETはなんで勝手にエスケープを変換するの?
    data[col_text] = (
        data[col_text]
        .str.replace("&amp;", "&", regex=False)
        # .str.replace("&", "&amp;", regex=False)
        .str.replace("<", "&lt;", regex=False)
        .str.replace(">", "&gt;", regex=False)
        .str.replace("゠", "=", regex=False)  # フォントが対応していない…
        # .str.replace("&amp;nbsp;", "&nbsp;")
        .str.replace("&nbsp;", "&amp;nbsp;")
        .str.replace("& ", "&amp;", regex=False)  # 和文で普通は使わないと思うが...
    )
    data[col_text_en] = (
        data[col_text_en]
        .str.replace("&amp;", "&", regex=False)
        .str.replace("<", "&lt;", regex=False)
        .str.replace(">", "&gt;", regex=False)
        .str.replace("゠", "=", regex=False)
        # .str.replace("&amp;nbsp;", "&nbsp;")
        .str.replace("&nbsp;", "&amp;nbsp;")
        .str.replace("& ", "&amp; ", regex=False)
    )
    return data


def replace_text(text_series: pd.Series, dictionary: pd.DataFrame) -> List[str]:
    """
    Args
    ------
    dictionary
        text, modified 列を持つpd.DataFrame
    """

    text_series = text_series.copy()
    for _, r in dictionary.iterrows():
        text_series = text_series.str.replace(
            str(r["text"]), str(r["modified"]), regex=True
        )
    return text_series


def get_words(
    data: pd.DataFrame, pat: regex.compile, col_text: str = "text"
) -> pd.DataFrame:
    # pandasのAPIのセンスのなさ
    df_words = (
        (
            data[["id", col_text]]
            .assign(
                words=lambda d: [extractall(str(x), pat) for x in d[col_text].values]
            )
            .groupby(["id"])
            .apply(
                lambda d: pd.DataFrame({"word": sum(d["words"].values.tolist(), [])}),
                include_groups=False,
            )
        )
        .reset_index()[["id", "word"]]
        .drop_duplicates()
        .sort_values(["word"])
    )
    df_words.groupby(["word"]).sum()
    return df_words


def extractall(x: str, pattern: regex.Pattern):
    return pattern.findall(x)


def filter_duplication(data: pd.DataFrame, col: str) -> pd.DataFrame:
    df_nunique = (
        data.groupby(["id"])[col]
        .nunique()
        .reset_index()
        .loc[lambda d: d[col] > 1]
        .rename(columns={col: "n_uniq"})
    )
    return data.merge(df_nunique, on=["id"])


def main(args: argparse.Namespace):
    dict_df_text = {}
    for col, fp, dp in [
        ("text", "fp_lang", args.dir_lang),
        ("text_CZ", "fp_CZ", args.dir_cz),
        ("text_EN", "fp_EN", args.dir_en),
    ]:
        print(f"searching {dp}")
        d = read_xmls(dp).rename(columns={"text2": col, "fp": fp})[["id", col, fp]]
        d_dup = filter_duplication(d, col)
        if d_dup.shape[0] != 0:
            print(f"{dp} id has duplications")
            d_dup.to_csv(f"tmp-{col}.csv", index=False)
        dict_df_text[col] = d
    del d, d_dup, col, fp, dp

    df = (
        dict_df_text["text_EN"]
        .merge(dict_df_text["text_CZ"], on=["id"], how="outer")
        .merge(dict_df_text["text"], on=["id"], how="outer")
        .assign(
            is_EN=lambda d: ~d["text_EN"].isna(),
            is_CZ=lambda d: ~d["text_CZ"].isna(),
            is_lang=lambda d: ~d["text"].isna(),
        )
        .assign(
            is_total=1,
            is_lang_cz=lambda d: d["is_lang"] & d["is_CZ"],
            is_en_cz=lambda d: d["is_EN"] & d["is_CZ"],
            is_lang_en=lambda d: d["is_lang"] & d["is_EN"],
            is_all=lambda d: d["is_lang"] & d["is_EN"] & d["is_CZ"],
        )
        .fillna("")
    )
    print(
        df[
            [
                "is_EN",
                "is_CZ",
                "is_lang",
                "is_lang_cz",
                "is_en_cz",
                "is_lang_en",
                "is_all",
            ]
        ].sum()
    )

    assert (
        df.loc[lambda d: d["id"].str.contains("_uiName$", regex=True)]
        .loc[lambda d: (d["is_lang"]) & (~d["is_CZ"])]
        .shape
        != 0
    ), "uiNames intersection is non null!"
    # 日本語テキストは変な改行タグが入っている
    df["text"] = np.where(
        df["fp_EN"] == "text_ui_dialog.xml",
        df["text"].str.replace("<br/>", " ", regex=False),
        df["text"],
    )

    # output original

    fp_terms = args.dir_interm.joinpath("terms.csv")
    print(f"writing to {fp_terms}")
    df.loc[
        lambda d: (d["id"].str.contains("_uiName$", regex=True))
        | (d["id"].str.contains("^location_", regex=True))
        | (d["id"].str.contains("^ui_nm_", regex=True))
        | (d["id"].str.contains("^ui_codex_name_", regex=True))
        | (d["id"].str.contains("^qname_", regex=True))
        | (d["id"].str.contains("^ui_maplegend_", regex=True))
        | (d["id"].str.contains("^ui_nh_", regex=True))
        | (d["id"].str.contains("^ui_item_info_", regex=True))
        | (d["id"].str.contains("^ui_item_category_", regex=True))
        | (d["id"].str.contains("^ui_hud_", regex=True))
        | (d["id"] == "ui_version_menu")
        | (d["id"].str.contains("^perk_", regex=True))
        | (d["id"].str.contains("^ui_tooltip_", regex=True))
        | (d["id"].str.contains("^ui_in_", regex=True))
        | (d["id"].str.contains("^perk_combo_", regex=True))
    ][["id", "text_EN", "text_CZ", "text"]].sort_values(["text"]).to_csv(
        fp_terms,
        index=False,
    )
    del fp_terms
    pat = regex.compile(r"[\p{katakana}ー゠・]+")
    fp_words = args.dir_root.joinpath("words.csv")
    print(f"writing to {fp_words}")
    get_words(df, pat).to_csv(fp_words, index=False)
    del fp_words

    dictionaries = read_dicts(args.dicts, args.dicts_id, args.dicts_rev)

    df_modified_all = translate(df, dictionaries)
    df_modified_all = escape_xml_symbols(df_modified_all)
    for col in ["text", "text_EN"]:
        assert (
            df_modified_all[col].isna().sum() == 0
        ), f"df_modified_all[{col}] contains {df_modified_all[col].isna().sum()} NaN"

    fp_words_after = args.dir_interm.joinpath("words-after.csv")
    print(f"""writing into {fp_words_after}""")
    summary_words = get_words(df_modified_all, pat)
    summary_words.groupby(["word"]).apply(lambda d: ",".join(d["id"])).reset_index(
        name="ids"
    ).to_csv(fp_words_after, index=False)
    fp_words_alph = args.dir_interm.joinpath("words-alphabet.csv")
    print(f"""writing into {fp_words_alph}""")
    summary_alphabet = df_modified_all.loc[
        lambda d: (~d["text"].isna())
        & (~d["id"].str.contains("^cr2_"))
        & (~d["id"].str.contains("^cr_"))
    ]
    summary_alphabet["text"] = (
        summary_alphabet["text"]
        .str.replace("amp;", "", regex=False)
        .str.replace("nbsp;", "", regex=False)
        .str.replace("gt;", "", regex=False)
        .str.replace("lt;", "", regex=False)
        .str.replace("br/", "", regex=False)
        .str.replace("/head", "", regex=False)
        .str.replace("/accent", "", regex=False)
        .str.replace("&[a-z]+?&", "", regex=False)
    )
    summary_alphabet = summary_alphabet.loc[
        lambda d: d["text"].str.contains("[A-Za-zÀ-ÖØ-öø-ÿ]"),
        ["id", "text_EN", "text_CZ", "text"],
    ]
    summary_alphabet.to_csv(fp_words_alph, index=False)

    if not args.dir_interm.joinpath("xml").exists():
        args.dir_interm.joinpath("xml").mkdir(parents=True)

    # for (fp,), d in df_modified_all.loc[
    #    lambda d: d["text"] != d["text_original"]
    # ].groupby(["fp_EN"]):
    #    xml = df_2_xml(d)
    #    print(f"""write to {args.dir_interm.joinpath(f"xml/{fp}")}""")
    #    xml.write(
    #        args.dir_interm.joinpath(f"xml/{fp}"),
    #        xml_declaration=True,
    #        encoding="utf-8",
    #    )
    df_modified_all.loc[
        lambda d: (d["id"].str.contains("^ui_codex_"))
        & ~(d["id"].str.contains("^ui_codex_name_"))
    ].to_csv(args.dir_interm.joinpath("text-codex.csv"), index=False)
    df_as_xml = df_modified_all.loc[
        lambda d: d["text"] != d["text_original"]
    ].drop_duplicates(["id"])
    print(
        f"{df_as_xml.shape[0]} entries will be output out of {df_modified_all.shape[0]} ({df_as_xml.shape[0]/df_modified_all.shape[0]:.2%}) %"
    )

    write_separately(df_as_xml, args.dir_out, args.xml_name)

    # xml = df_2_xml(df_as_xml)
    # print(f"""write to {args.dir_out.joinpath(f"{args.xml_name}.xml")}""")
    # if not args.dir_out.exists():
    #    args.dir_out.mkdir(parents=True)

    # xml.write(
    #    args.dir_out.joinpath("text_AltJPTranslation.xml"),
    #    xml_declaration=True,
    #    encoding="utf-8",
    # )


def translate(data: pd.DataFrame, dicts: TranslationDicts) -> pd.DataFrame:
    """
    DFに変換したXMLと辞書データを比較して一致する箇所を置換して返す
    Args
    -----
    data: pd.DataFrame
        以下の列を持つ
        id
        text,
        text_EN,
        text_CZ,
        fp_lang,
        fp_EN,
        fp_CZ
    """
    data["text_original"] = data["text"]
    df_modified_id = data.merge(
        dicts.by_id[["id", "modified"]],
        on=["id"],
        how="inner",
    ).assign(text=lambda d: np.where(d["modified"].isna(), d["text"], d["modified"]))[
        ["id", "text_EN", "text", "fp_lang", "fp_EN", "fp_CZ"]
    ]
    df_modified_left = data.merge(
        dicts.by_id[["id"]].assign(flag=True), on=["id"], how="left"
    ).loc[lambda d: d["flag"].isna()]

    # IDが一致しなかった残りのフィールドに対して単純変換する
    # 文字数大きいものから変換したほうが誤爆しにくいだろう...

    s_text = replace_text(df_modified_left["text"], dicts.by_match)
    df_modified_left["text"] = s_text
    s_text = replace_text(df_modified_left["text"], dicts.rev_by_match)
    df_modified_left["text"] = s_text
    df_modified_all = pd.concat((df_modified_id, df_modified_left))
    return df_modified_all


def read_dicts(
    fp_dicts: Path, fp_dicts_id: Path, fp_dicts_rev: Path
) -> TranslationDicts:
    """
    idは内容の変更に関係なく適用する
    条件一致は変更してないエントリーを除外する
    """

    def _read_csv_with_print_name(fp: Path) -> pd.DataFrame:
        print(f"""reading {fp}""")
        return pd.read_csv(fp)

    _df_dict = pd.concat(
        [_read_csv_with_print_name(fp) for fp in fp_dicts.glob("*.csv")]
    ).loc[lambda d: ~d["modified"].isna()]
    _df_dict_id = (
        pd.concat([_read_csv_with_print_name(fp) for fp in fp_dicts_id.glob("*.csv")])
        .loc[lambda d: ~d["modified"].isna()]
        .assign(onlyid=lambda d: d["onlyid"].fillna(0))
    )
    df_dict_rev = pd.concat(
        [_read_csv_with_print_name(fp) for fp in fp_dicts_rev.glob("*.csv")]
    )
    df_by_id = pd.concat(
        (
            _df_dict.loc[
                lambda d: (~d["id"].isna()) & (~d["modified"].isna())
            ],  # これがないとpandasは発狂する
            _df_dict_id.loc[lambda d: (~d["id"].isna()) & (~d["modified"].isna())],
        )
    )[["id", "modified"]].reset_index(drop=True)
    df_by_match = (
        pd.concat((_df_dict_id.loc[lambda d: ~(d["onlyid"] == 1)], _df_dict))
        .loc[
            lambda d: (d["text"] != d["modified"])
            & (d["onlyid"] != 1)
            & (~d["text"].isna() & ~d["modified"].isna())
        ][["text", "modified"]]
        .drop_duplicates()
        .assign(n_words=lambda d: d["modified"].str.len())
        .sort_values(["n_words"], ascending=False)
        .drop(columns=["n_words"])
    )
    return TranslationDicts(df_by_id, df_by_match, df_dict_rev)


def write_separately(data: pd.DataFrame, output_dir: Path, base_name: str) -> None:
    """
    テキストデータを適当なXMLファイルに分割して保存する.
    TODO: 全部1つのファイルにいれるとなぜかうまく読み込まれなかった. ファイルサイズか何かに制約がある?
    """
    for pattern, suffix in OUTFILE:
        df_sub = data.loc[lambda d: d["id"].str.contains(pattern, regex=True)]
        data = (
            data.merge(df_sub[["id"]].assign(anti=True), on=["id"], how="left")
            .assign(
                anti=lambda d: np.where(d["anti"] == True, True, False)
            )  # np.nan が暗黙的にTrueになるし、明示的に条件式書いたら結果が変わる.
            .loc[lambda d: ~(d["anti"])]
            .drop(columns=["anti"])
        )
        xml = df_2_xml(df_sub)
        fp_xml = output_dir.joinpath(f"text_{base_name}_{suffix}.xml")
        print(f"""write to {fp_xml} ({df_sub.shape[0]} entries)""")
        if not output_dir.exists():
            output_dir.mkdir(parents=True)

        xml.write(
            fp_xml,
            xml_declaration=True,
            encoding="utf-8",
        )
    xml = df_2_xml(data)
    fp_xml = output_dir.joinpath(f"text_{base_name}.xml")
    print(f"""write to {fp_xml} ({data.shape[0]} entries)""")
    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    xml.write(
        fp_xml,
        xml_declaration=True,
        encoding="utf-8",
    )


if __name__ == "__main__":
    args = parser.parse_args()
    args_new = rename_args(args)
    main(args_new)
