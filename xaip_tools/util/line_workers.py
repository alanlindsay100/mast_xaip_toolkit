

# import shared_util
# import shared_util.line_workers as LINE_WORKER
# LINE_WORKER.gather_until_match(lines, lambda x: x.startswith("@"), True, True)

def gather_until_match(things, matcher, remove_empty=True,yield_final=False,retain_matcher=False):
  lump = []
  for t in things:
    if matcher(t) :
      if not remove_empty or len(lump) > 0:
        yield lump
      lump = list()
      if retain_matcher:
        lump.append(t)
    else :
      t = t.strip()
      if remove_empty:
        if t == "":
          continue
      
      lump.append(t)
  if yield_final and len(lump) > 0:
    yield lump
  return



