import argparse
import os
import sys
import json
from datetime import date
from collections import defaultdict, Counter
from tqdm import tqdm
import pandas as pd
def get_program_seq(program):
    seq = []
    for item in program:
        func = item['function']
        inputs = item['inputs']
        args = ''
        for input in inputs:
            args += ' <arg> ' + input
        seq.append(func + args)
    seq = ' <func> '.join(seq)
    return seq
def whether_equal(answer, pred):
    def truncate_float(x):
        # convert answer from '100.0 meters' to '100 meters'
        try:
            v, *u = x.split()
            v = float(v)
            if v - int(v) < 1e-5:
                v = int(v)
            if len(u) == 0:
                x = str(v)
            else:
                x = '{} {}'.format(str(v), ' '.join(u))
        except:
            pass
        return x

    def equal_as_date(x, y):
        # check whether x and y are equal as type of date or year
        try:
            x_split = x.split('-')
            y_split = y.split('-')
            if len(x_split) == 3:
                x = date(int(x_split[0]), int(x_split[1]), int(x_split[2]))
            else:
                x = int(x)
            if len(y_split) == 3:
                y = date(int(y_split[0]), int(y_split[1]), int(y_split[2]))
            else:
                y = int(y)
            if isinstance(x, date) and isinstance(y, date):
                return x == y
            else:
                x = x.year if isinstance(x, date) else x
                y = y.year if isinstance(y, date) else y
                return x == y
        except:
            return False

    answer = truncate_float(answer)
    pred = truncate_float(pred)
    if equal_as_date(answer, pred):
        return True
    else:
        return answer == pred


def load(f):
    data = []
    for line in f:
        data.append(json.loads(line.strip()))
    return data
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--gt_folder',default='./dataset/plus_subset/')
    parser.add_argument('--pred_fn',default='./output/only_intermedia/')

    args=parser.parse_args()

    predict_file_name='predict-teacher_ckpt.txt'
    # predict_kopl_filename='predict-kopl-checkpoint-235960.txt'
    # ckpt_num=predict_file_name.split('-')[-1].replace('.txt','')
    gt_folder, pred_fn = args.gt_folder,args.pred_fn

    gt_fn = os.path.join(gt_folder, 'parallel_test.json')
    gt = json.load(open(gt_fn))
    pred = [x.strip() for x in open(os.path.join(pred_fn,predict_file_name)).readlines()] # one prediction per line
    # pred_kopls=[x.strip() for x in open(os.path.join(pred_fn,predict_kopl_filename)).readlines()]
    train_set = json.load(open(os.path.join(gt_folder, 'parallel_train.json')))
    train_answer_set = set(x['answer'] for x in train_set)

    labels = ['overall', 'multihop', 'qualifier', 'comparison', 'logical', 'count', 'verify', 'zero-shot']
    total = {k:0 for k in labels}
    correct = {k:0 for k in labels}

    headers=['question','golden_kopl','golden_answer','pred_kopl','pred_answer']
    error_df=pd.DataFrame(columns=headers)

    for i in tqdm(range(len(pred))):
        cur_labels = ['overall']
        functions = [f['function'] for f in gt[i]['program']]
        question=gt[i]['rewrite']
        dcs = gt[i]['lambda-dcs']
        if (dcs == ''):
            continue


        for f in functions:
            if f in {'Relate'} or f.startswith('Filter'):
                cur_labels.append('multihop')
                break
        for f in functions:
            if f in {'QFilterStr', 'QFilterNum', 'QFilterYear', 'QFilterDate', 'QueryAttrUnderCondition', 'QueryAttrQualifier', 'QueryRelationQualifier'}:
                cur_labels.append('qualifier')
                break
        for f in functions:
            if f in {'Select','SelectBetween'}:
                cur_labels.append('comparison')
                break
        for f in functions:
            if f in {'And', 'Or'}:
                cur_labels.append('logical')
                break
        for f in functions:
            if f in {'Count'}:
                cur_labels.append('count')
                break
        for f in functions:
            if f in {'VerifyStr','VerifyNum','VerifyYear','VerifyDate'}:
                cur_labels.append('verify')
                break

        answer = gt[i]['answer']
        if answer not in train_answer_set:
            cur_labels.append('zero-shot')
        if whether_equal(answer, pred[i]):
            for k in cur_labels:
                correct[k] += 1
        # else:
        #     pass
        #     append_result=gt[i]
        #
        #     question=append_result['rewrite']
        #
        #
        #     golden_kopl=gt[i]['program']
        #     golden_kopl=get_program_seq(golden_kopl)
        #     golden_answer = append_result['answer']
        #
        #     pred_kopl=pred_kopls[i]
        #     pred_answer=pred[i]
        #
        #     # append_result['golden_kopl']=golden_kopl
        #     # append_result['pred_kopl'] = pred_kopl
        #     append_data=[question,golden_kopl,golden_answer,pred_kopl,pred_answer]
        #
        #
        #     error_df.loc[len(error_df)]=append_data
        for k in cur_labels:
            total[k] += 1

    with open(os.path.join(pred_fn,'predict'+'_teacher_ckpt_acc.txt'),'w',encoding='utf-8') as f:
        for k in labels:
            if(total[k]==0):
                continue
            print('{}: {:.2f}% ({}/{})'.format(k, correct[k]/total[k]*100, correct[k], total[k]))
            f.write('{}: {:.2f}% ({}/{})'.format(k, correct[k]/total[k]*100, correct[k], total[k])+'\n')

    # error_df.to_excel(os.path.join(pred_fn,'predict_error_'+str(ckpt_num)+'.xlsx'),index=False)
    if len(pred) < len(gt):
        print('WARNING: there are only {} predictions (need {})'.format(len(pred), len(gt)))


if __name__ == '__main__':
    main()
