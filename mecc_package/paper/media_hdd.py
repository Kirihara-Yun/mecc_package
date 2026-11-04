"""Audience-facing wording for the measured rotational block-device setup.

Keep names of cited SSD systems intact; only the MECC deployment and local
adapter labels change. This module does not relabel experimental JSON keys.
"""


def display_text(value: str) -> str:
    value = value.replace('SSD-LLaMA', '\u0001').replace('SSD-LLama', '\u0002')
    value = (value.replace('SSD-native adapter', 'HDD-backed cache adapter')
                 .replace('SSD-native', 'HDD-backed cache adapter')
                 .replace('SSD 缓存基线', 'HDD 缓存基线')
                 .replace('SSD-active', 'HDD-backed')
                 .replace('SSD', 'HDD'))
    return value.replace('\u0001', 'SSD-LLaMA').replace('\u0002', 'SSD-LLama')


def figure_text(fig) -> None:
    from matplotlib.text import Text
    for artist in fig.findobj(match=Text):
        before = artist.get_text()
        after = display_text(before)
        if after != before:
            artist.set_text(after)


def manuscript_text(value: str) -> str:
    """Change this paper's setup while preserving the related-work section."""
    start = value.find('\\section{Related Work}')
    end = value.find('\\section{Conclusion}', start) if start >= 0 else -1
    if start < 0 or end < 0:
        raise ValueError('paper section boundaries changed')
    first = value[:start].replace('SSD-native delivery', '\u0003')
    first = first.replace('NVMe/SSD measurement', '\u0004')
    first = (display_text(first).replace('\u0003', 'SSD-native delivery')
                               .replace('\u0004', 'NVMe/SSD measurement'))
    last = display_text(value[end:])
    related = value[start:end].replace('The scope is SSD-active single-GPU serving.',
                                       'The scope is HDD-backed single-GPU serving.')
    related = related.replace('Local adapters do not establish superiority over these systems. \n',
                              'Local adapters do not establish superiority over these systems.\n')
    return first + related + last
