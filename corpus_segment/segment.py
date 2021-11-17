from pathlib import Path
import re

from botok import ChunkTokenizer, WordTokenizer, Config
import yaml


class PrepareCorpus:
    def __init__(self, corpus_path, yaml_path, chunk_size=300):
        self.in_path = Path(corpus_path)
        self.out_path = Path(yaml_path)
        self.size = chunk_size

    @staticmethod
    def get_syls(string):
        string = string.replace('\n', '')
        chunks = ChunkTokenizer(string).tokenize()
        bo_chunks = [c for c in chunks if c[0] == 'TEXT' or c[0] == 'PUNCT']
        return bo_chunks

    def get_chunks(self, syls):
        chunks = {}
        c_num = 1
        start = 0
        end = 0
        while end <= len(syls):
            end = start + self.size

            while end <= len(syls) and syls[end][0] != 'PUNCT':
                end += 1
            else:
                end += 1

            chunk = ''.join([s[1] for s in syls[start:end]]).strip()
            chunk = chunk[1:] if chunk.startswith('\ufeff') else chunk
            if chunk:
                chunks[c_num] = chunk
            c_num += 1
            start = end

        return chunks

    def prepare_chunks(self):
        output = {}
        for f in self.in_path.glob('*'):
            syls = self.get_syls(f.read_text())
            chunks = self.get_chunks(syls)

            output[f.name] = chunks

        total = 0
        for f, chunks in output.items():
            total += len(chunks)
        out = {'total': total}
        out.update(output)

        yaml_out = yaml.dump(out, allow_unicode=True, sort_keys=False)
        self.out_path.write_text(yaml_out)


class SegmentCorpus:
    def __init__(self, yaml_file, new_corpus=False):
        self.new = new_corpus
        self.chunks_path = Path(yaml_file)
        self.seg_corp_path = self.chunks_path.parent / (self.chunks_path.stem + '/')
        self.config = self.chunks_path.parent / (self.chunks_path.stem + '.config')
        self.current_window = self.chunks_path.parent / (self.chunks_path.stem + '_current.txt')
        self.state = {'total': 0, 'done': 0, 'current_file': None, 'current_chunk': 0}
        self.chunks = None
        self.setup_corpus()
        self.tok_data_path = None
        self.tok = self.set_tok()

    def set_tok(self):
        path = self.chunks_path.parent / 'tok_data'
        self.tok_data_path = path
        c = Config(dialect_name='general', base_path=path)
        return WordTokenizer(config=c)

    def setup_corpus(self):
        # load chunks
        self.chunks = yaml.safe_load(self.chunks_path.read_text())

        if self.new:
            # create the config path
            self.state['total'] = self.chunks['total']
            conf = yaml.dump(self.state, allow_unicode=True, sort_keys=False)
            self.config.write_text(conf)
            # create the segmented corpus folder or empty it
            if not self.seg_corp_path.is_dir():
                self.seg_corp_path.mkdir()
            else:
                for f in self.seg_corp_path.glob('*'):
                    f.unlink()

        else:
            # load config into state
            conf = yaml.safe_load(self.config.read_text())
            if conf:
                for f, c in conf.items():
                    self.state[f] = c

    def tokenize(self, current):
        lemmatization_exceptions = ['བཅས་', 'མཁས་']
        tokens = self.tok.tokenize(current)
        words = []
        for t in tokens:
            if t.chunk_type == 'TEXT':
                if not t.lemma:
                    text = t.text
                else:
                    if t.pos == 'PART':
                        if t.affix:
                            text = '-' + t.text
                        else:
                            text = t.text
                    else:
                        # Hack because of botok limitation:
                        if t.text not in lemmatization_exceptions and t.affixation and 'aa' in t.affixation and t.affixation['aa']:
                            text = t.lemma
                        else:
                            text = t.text
                text = text.strip().replace('༌', '་')
                if not text.endswith('་'):
                    text += '་'

                if t.pos == 'NON_WORD':
                    text += '#'
                words.append(text)

            else:
                t = t.text.strip().replace(' ', '_')
                words.append(t)

        tokenized = ' '.join(words)

        # do replacements
        repl_path = self.tok_data_path / 'general' / 'adjustments' / 'rules' / 'replacements.txt'
        for line in repl_path.read_text().split('\n'):
            orig, repl = line.split('—')
            tokenized = tokenized.replace(orig, repl)

        return tokenized

    def update_data(self, words, file):
        if not file.is_file():
            file.write_text('')
        dump = file.read_text()
        dump += '\n' + '\n'.join(words)
        file.write_text(dump)

    def process_adjustments(self, dump):
        to_add = []
        to_remove = []
        # (xxx {xxx/ xxx} pattern
        double_adjs_a = re.findall(r'\(.+? \{.+?[\/\+] .+?\}', dump)
        for d in double_adjs_a:
            parts = re.split(r'\((.+?) \{(.+?)([\/\+]) (.+?)\}', d)
            a, b, op, c = [p for p in parts if p]
            for el in [a, b, c]:
                if el.startswith('སྤྱོད་འཇུག'):
                    print()
            word1, word2 = a + b, b + c
            if op == '+':
                to_add.append(word1)
            elif op == '/':
                to_remove.append(word1)
            to_add.append(word2)
            adjusted = f'{a} {b}{c}'
            dump = dump.replace(d, adjusted)
        # {xxx (xxx} xxx/ pattern
        double_adjs_a = re.findall(r'\{.+? \(.+?\} .+?[\/\+]', dump)
        for d in double_adjs_a:
            parts = re.split(r'\{(.+?) \((.+?)\} (.+?)([\/\+])', d)
            a, b, c, op = [p for p in parts if p]
            for el in [a, b, c]:
                if el.startswith('སྤྱོད་འཇུག'):
                    print()
            word2, word1 = a + b, b + c
            if op == '+':
                to_add.append(word1)
            elif op == '/':
                to_remove.append(word1)
            to_add.append(word2)
            adjusted = f'{a}{b} {c}'
            dump = dump.replace(d, adjusted)
        # (xxx xxx/ patterns
        adjs = re.findall(r'(\((([^ ]+ )+?[^ ]+)([\+\/]+?))', dump)
        for a in adjs:
            raw, text, _, op = a
            if text.startswith('སྤྱོད་འཇུག'):
                print()

            if op == '+':
                if '-' in text:
                    text = text.replace('་ -', '')
                to_add.append(text.replace('-', ''))
                text = text.replace(' ', '')
            elif op == '/':
                to_remove.append(text.replace('-', ''))
            # clean output
            if not text.endswith('་'):
                text += '་'
            dump = dump.replace(raw, text)
        # xxx/ patterns
        adjs = re.findall(r'([^ ]+)([\+\/])', dump)
        for a in adjs:
            raw = a[0]
            text, op = [l for l in list(a[1:]) if l]
            if text.startswith('སྤྱོད་འཇུག'):
                print()

            if op == '+':
                if '-' in text:
                    text = text.replace('་ -', '')
                to_add.append(text.replace('-', ''))
                text = text.replace(' ', '')
            elif op == '/':
                to_remove.append(text.replace('-', ''))
            # clean output
            if not text.endswith('་'):
                text += '་'
            dump = dump.replace(raw, text)
        if to_add:
            to_add_file = self.tok_data_path / 'general' / 'adjustments' / 'words' / (self.chunks_path.stem + '.tsv')
            self.update_data(to_add, to_add_file)
        if to_remove:
            to_remove_file = self.tok_data_path / 'general' / 'adjustments' / 'remove' / (self.chunks_path.stem + '.tsv')
            self.update_data(to_remove, to_remove_file)
        return dump

    def seg_window(self):
        for f_name, file_chunks in self.chunks.items():
            # prepare
            #############################################
            if f_name == 'total':
                continue

            if not self.state['current_file']:
                self.state['current_file'] = f_name

            if not self.state['current_chunk']:
                self.state['current_chunk'] = 1

            # process
            ##############################################
            # save well segmented chunk
            out_file = self.seg_corp_path / str(self.state['current_file'])
            if not out_file.is_file():
                out_file.write_text('')
            else:
                print(f'\tsaving: {self.state["current_chunk"]}, {self.state["current_file"]}')
                adjusted_window = self.process_adjustments(self.current_window.read_text())
                out = f'{out_file.read_text()}\n{adjusted_window}'
                out_file.write_text(out)
                self.state['current_chunk'] += 1
                self.state['done'] += 1
                c_file_total = len(self.chunks[self.state['current_file']])
                print(f'finished: {100*self.state["done"]/self.state["total"]}% {self.state["done"]} out of '
                      f'{self.state["total"]} chunks.\n{100*self.state["current_chunk"]/c_file_total}% of {self.state["current_file"]}')

            # segment and review
            if self.state['current_file'] == f_name:
                for c_num, chunk in file_chunks.items():
                    if self.state['current_chunk'] == c_num:
                        print(f'\tsegmenting: {self.state["current_chunk"]}, {self.state["current_file"]}')
                        tokenized = self.tokenize(chunk)
                        self.current_window.write_text(tokenized)
                        break
            break

        # save state to config
        self.config.write_text(yaml.dump(self.state, allow_unicode=True, sort_keys=False))
