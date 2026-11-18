"""Review one demand alert at hourly resolution: is the flagged day consistent with its weather and calendar
context, or does a deviation remain in a specific period?

The daily detector (``swissgrid_cot.annotate``) decides which days to flag. This package compares the
flagged day's 24 local hours with references built from earlier days only.
"""
