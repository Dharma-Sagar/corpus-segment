from pathlib import Path

from corpus_segment import PrepareCorpus, SegmentCorpus


def segment_corpus(in_path, chunks_path, new=False):
    # chunk corpus in more or less 300 syls chunks saved as .yaml
    if not Path(chunks_path).is_file():
        pc = PrepareCorpus(in_path, chunks_path)
        pc.prepare_chunks()

    # load corpus to segment
    sc = SegmentCorpus(chunks_path, new_corpus=new)  # if new, create config file etc.

    # process current window
    sc.seg_window()


if __name__ == '__main__':
    in_path = 'input'
    chunks_path = 'output/chunks.yaml'
    segment_corpus(in_path, chunks_path)
