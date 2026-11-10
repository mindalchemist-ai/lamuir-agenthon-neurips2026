import os
import re
import stat
import sys
import unicodedata

MIB = 1 << 20


def problems(root):
    found, names = [], {}
    files = entries = total = 0
    for here, dirs, fs in os.walk(root, followlinks=False):
        for name in dirs + fs:
            path = os.path.join(here, name)
            rel = os.path.relpath(path, root)
            entries += 1
            st = os.lstat(path)
            depth = rel.count(os.sep) + 1
            if stat.S_ISDIR(st.st_mode) and depth >= 8:
                found.append(f"folder nested 8+ levels: {rel}")
            if stat.S_ISREG(st.st_mode) and depth > 8:
                found.append(f"file more than seven folders down: {rel}")
            if stat.S_ISLNK(st.st_mode):
                found.append(f"symbolic link: {rel}")
            elif not (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)):
                found.append(f"special file: {rel}")
            if stat.S_ISREG(st.st_mode):
                files += 1
                total += st.st_size
                if st.st_nlink > 1:
                    found.append(f"hard link: {rel}")
                if st.st_size > 64 * MIB:
                    found.append(f"file over 64 MiB: {rel}")
                if st.st_size > 64 * max(st.st_blocks * 512, 4096):
                    found.append(f"sparse file: {rel}")
            if stat.S_ISREG(st.st_mode) and st.st_mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX):
                found.append(f"setuid/setgid/sticky bit: {rel}")
            try:
                name.encode("utf-8")
            except UnicodeEncodeError:
                found.append(f"name not valid UTF-8: {rel!r}")
                continue
            if unicodedata.normalize("NFC", name) != name:
                found.append(f"name not in NFC form: {rel}")
            if "\\" in name or any(ord(c) < 32 or ord(c) == 127 for c in name):
                found.append(f"backslash or control character in name: {rel}")
            if here == root and re.match(r"^[A-Za-z]:", name):
                found.append(f"drive-like name: {rel}")
            key = unicodedata.normalize("NFC", rel).casefold()
            if key in names and names[key] != rel:
                found.append(f"paths differ only in case or Unicode form: {names[key]} / {rel}")
            names.setdefault(key, rel)
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(here, d))]
    if files > 256:
        found.append(f"{files} files (limit 256)")
    if entries > 4096:
        found.append(f"{entries} files and folders (limit 4096)")
    if total > 64 * MIB:
        found.append(f"{total / MIB:.1f} MiB in total (limit 64)")
    if files == 0:
        found.append("no files")
    return found


def main():
    refused = 0
    for root in sys.argv[1:]:
        found = problems(root)
        if found:
            refused += 1
            print(f"REFUSED {root}: " + "; ".join(sorted(set(found))[:5]))
    print(f"checked {len(sys.argv) - 1} folders, refused {refused}")
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
