import os
import json
import pickle
import argparse
import numpy as np
from nltk import word_tokenize
from collections import Counter
from itertools import chain
from tqdm import tqdm
import re

from misc import init_vocab
from transformers import *


def get_program_seq(program):
    seq = []
    for item in program:
        func = item['function']
        inputs = item['inputs']
        seq.append(func + '(' + '<c>'.join(inputs) + ')')
    seq = '<b>'.join(seq)
    # print(program)
    # print(seq)
    return seq


def encode_dataset(dataset, vocab, tokenizer, test = False):
    questions = []
    programs = []
    for item in tqdm(dataset):
        question = item['rewrite']
        questions.append(question)
        if not test:
            program = item['program']
            program = get_program_seq(program)
            programs.append(program)
    sequences = questions + programs
    encoded_inputs = tokenizer(sequences, padding = True)
    print(encoded_inputs.keys())
    print(encoded_inputs['input_ids'][0])
    print(tokenizer.decode(encoded_inputs['input_ids'][0]))
    print(tokenizer.decode(encoded_inputs['input_ids'][-1]))
    max_seq_length = len(encoded_inputs['input_ids'][0])
    assert max_seq_length == len(encoded_inputs['input_ids'][-1])
    print(max_seq_length)
    questions = []
    programs = []
    choices = []
    answers = []
    for item in tqdm(dataset):
        question = item['rewrite']
        questions.append(question)
        _ = [vocab['answer_token_to_idx'][w] for w in item['choices']]
        choices.append(_)
        if not test:
            program = item['program']
            program = get_program_seq(program)
            programs.append(program)
            answers.append(vocab['answer_token_to_idx'].get(item['answer']))

    input_ids = tokenizer.batch_encode_plus(questions, max_length = max_seq_length, pad_to_max_length = True, truncation = True)
    source_ids = np.array(input_ids['input_ids'], dtype = np.int32)
    source_mask = np.array(input_ids['attention_mask'], dtype = np.int32)
    if not test:
        target_ids = tokenizer.batch_encode_plus(programs, max_length = max_seq_length, pad_to_max_length = True, truncation = True)
        target_ids = np.array(target_ids['input_ids'], dtype = np.int32)
    else:
        target_ids = np.array([], dtype = np.int32)
    choices = np.array(choices, dtype = np.int32)
    answers = np.array(answers, dtype = np.int32)
    return source_ids, source_mask, target_ids, choices, answers



def main():
    parser = argparse.ArgumentParser()
    # parser.add_argument('--input_dir', default='./Bart_DCS_50/parallel_cover_50')
    parser.add_argument('--input_dir', default='./dataset/plus_subset')
    # parser.add_argument('--output_dir', default='./try_cycle_generation/multi_teacher/Stage_2_3_three_teacher_selfkopl_encoder_sparql_dcs/preprocessed_data')
    parser.add_argument('--output_dir', default='./dataset/plus_subset/preprocessed_data')
    parser.add_argument('--model_name_or_path', default='./Migration_experiment/baseline(Bart)/checkpoint')
    args = parser.parse_args()

    print('Build kb vocabulary')
    vocab = {
        'answer_token_to_idx': {}
    }
    print('Load questions')
    train_set = json.load(open(os.path.join(args.input_dir, 'parallel_train.json')))
    val_set = json.load(open(os.path.join(args.input_dir, 'parallel_val.json')))
    test_set = json.load(open(os.path.join(args.input_dir, 'parallel_test.json')))
    for question in chain(train_set, val_set, test_set):
        for a in question['choices']:
            if not a in vocab['answer_token_to_idx']:
                vocab['answer_token_to_idx'][a] = len(vocab['answer_token_to_idx'])

    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)
    fn = os.path.join(args.output_dir, 'vocab.json')
    print('Dump vocab to {}'.format(fn))
    with open(fn, 'w') as f:
        json.dump(vocab, f, indent=2)
    for k in vocab:
        print('{}:{}'.format(k, len(vocab[k])))
    tokenizer = BartTokenizer.from_pretrained(args.model_name_or_path)
    for name, dataset in zip(('train', 'val', 'test'), (train_set, val_set, test_set)):
        print('Encode {} set'.format(name))
        outputs = encode_dataset(dataset, vocab, tokenizer, name=='test')
        assert len(outputs) == 5
        print('shape of input_ids of questions, attention_mask of questions, input_ids of kopls, choices and answers:')
        with open(os.path.join(args.output_dir, '{}.pt'.format(name)), 'wb') as f:
            for o in outputs:
                print(o.shape)
                pickle.dump(o, f)


if __name__ == '__main__':
    main()
