import argparse
from pathlib import Path
from typing import Optional

parser = argparse.ArgumentParser()
parser.add_argument("dir_root", type=Path, default=Path("./"))
parser.add_argument("--intermediate", type=Path, default=None)
parser.add_argument("--dir-lang", type=Path, default=None)
parser.add_argument("--dir-cz", type=Path, default=None)
parser.add_argument("--dicts", type=Path, default=None)
parser.add_argument("--dicts-id", type=Path, default=None)
parser.add_argument("--dicts-rev", type=Path, default=None)
parser.add_argument("--dir-out", type=Path, default=None)
parser.add_argument("--xml-name", type=Path, default=None)


def rename_args(args_base: argparse.Namespace) -> argparse.Namespace:
    def _append_path(path: Path, appendee: Optional[Path], fp_default: str):
        return path.joinpath(fp_default) if appendee is None else appendee

    args_new = argparse.Namespace
    args_new.dir_root = args_base.dir_root
    args_new.dir_interm = _append_path(
        args_base.dir_root, args_base.intermediate, "private/intermediate"
    )
    args_new.dir_lang = _append_path(
        args_new.dir_root, args_base.dir_lang, "private/Japanese_xml"
    )
    args_new.dir_cz = _append_path(
        args_new.dir_root, args_base.dir_cz, "private/Czech_xml"
    )
    args_new.dicts = _append_path(args_new.dir_root, args_base.dicts, "dicts")
    args_new.dicts_id = _append_path(args_new.dir_root, args_base.dicts, "dicts-id")
    args_new.dicts_rev = _append_path(
        args_new.dir_root, args_base.dicts_rev, "dicts-rev"
    )
    args_new.dir_out = _append_path(args_new.dir_root, args_base.dir_out, "output")
    args_new.xml_name = (
        "AltJPTranslation" if args_base.xml_name is None else args_base.xml_name
    )
    return args_new
