from pathlib import Path

data = Path(__file__).parent.parent / 'data'

dutch = data / 'DPW.CD'
english = data / 'EPW.CD'
german = data / 'GPW.CD'

dutch_header = data / 'dutch_header'
english_header = data / 'english_header'
german_header = data / 'german_header'
