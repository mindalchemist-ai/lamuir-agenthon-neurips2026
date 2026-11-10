# Scoring text against word lists

When text is scored against word lists, lowercase and split on word characters (for example `re.findall(r"[a-z']+", text.lower())`), so punctuation attached to a word does not stop a match.
