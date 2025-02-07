import os
import torch
import torch.optim as optim
import torch.nn as nn
import argparse
import shutil
import json
from tqdm import tqdm
from datetime import date
from misc import MetricLogger, seed_everything, ProgressBar
from load_kb import DataForSPARQL
from data import DataLoader
from transformers import BartConfig, BartForConditionalGeneration, BartTokenizer
import torch.optim as optim
import logging
import time
from lr_scheduler import get_linear_schedule_with_warmup
import re
from executor_rule import RuleExecutor
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s')
logFormatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
rootLogger = logging.getLogger()
import warnings
warnings.simplefilter("ignore") # hide warnings that caused by invalid sparql query


def post_process(text):
    pattern = re.compile(r'".*?"')
    nes = []
    for item in pattern.finditer(text):
        nes.append((item.group(), item.span()))
    pos = [0]
    for name, span in nes:
        pos += [span[0], span[1]]
    pos.append(len(text))
    assert len(pos) % 2 == 0
    assert len(pos) / 2 == len(nes) + 1
    chunks = [text[pos[i]: pos[i+1]] for i in range(0, len(pos), 2)]
    for i in range(len(chunks)):
        chunks[i] = chunks[i].replace('?', ' ?').replace('.', ' .')
    bingo = ''
    for i in range(len(chunks) - 1):
        bingo += chunks[i] + nes[i][0]
    bingo += chunks[-1]
    return bingo

def vis(args, kb, model, data, device, tokenizer):
    while True:
        # text = 'Who is the father of Tony?'
        # text = 'Donald Trump married Tony, where is the place?'
        text = input('Input your question:')
        with torch.no_grad():
            input_ids = tokenizer.batch_encode_plus([text], max_length = 512, pad_to_max_length = True, return_tensors="pt", truncation = True)
            source_ids = input_ids['input_ids'].to(device)
            outputs = model.generate(
                input_ids=source_ids,
                max_length = 500,
            )
            outputs = [tokenizer.decode(output_id, skip_special_tokens = True, clean_up_tokenization_spaces = True) for output_id in outputs]
            outputs = [post_process(output) for output in outputs]
            print(outputs[0])

# def predict(args, kb, model, data, device, tokenizer, executor):
#     model.eval()
#     count, correct = 0, 0
#     pattern = re.compile(r'(.*?)\((.*?)\)')
#     # torch.no_grad() 是一个上下文管理器，被该语句 wrap 起来的部分将不会track 梯度
#     # 详解https://blog.csdn.net/weixin_46559271/article/details/105658654
#     with torch.no_grad():
#         all_outputs = []
#         for batch in tqdm(data, total=len(data)):
#             batch = batch[:3]
#             source_ids, source_mask, choices = [x.to(device) for x in batch]
#             outputs = model.generate(
#                 input_ids=source_ids,
#                 max_length = 500,
#             )
#
#             all_outputs.extend(outputs.cpu().numpy())
#             # break
#
#         outputs = [tokenizer.decode(output_id, skip_special_tokens = True, clean_up_tokenization_spaces = True) for output_id in all_outputs]
#         # questions = [tokenizer.decode(source_id, skip_special_tokens = True, clean_up_tokenization_spaces = True) for source_id in all_answers]
#         with open(os.path.join(args.save_dir, 'predict.txt'), 'w') as f:
#             for output in tqdm(outputs):
#                 chunks = output.split('<b>')
#                 func_list = []
#                 inputs_list = []
#                 for chunk in chunks:
#                     # print(chunk)
#                     res = pattern.findall(chunk)
#                     # print(res)
#                     if len(res) == 0:
#                         continue
#                     res = res[0]
#                     func, inputs = res[0], res[1]
#                     if inputs == '':
#                         inputs = []
#                     else:
#                         inputs = inputs.split('<c>')
#
#                     func_list.append(func)
#                     inputs_list.append(inputs)
#                 ans = executor.forward(func_list, inputs_list, ignore_error = True)
#                 if ans == None:
#                     ans = 'no'
#                 f.write(ans + '\n')


# def validate(args, kb, model, data, device, tokenizer, executor):
#     model.eval()
#     count, correct = 0, 0
#     pattern = re.compile(r'(.*?)\((.*?)\)')
#     with torch.no_grad():
#         all_outputs = []
#         all_answers = []
#         for batch in tqdm(data, total=len(data)):
#             source_ids, source_mask, choices, target_ids, answer = [x.to(device) for x in batch]
#             outputs = model.generate(
#                 input_ids=source_ids,
#                 max_length = 500,
#             )

#             all_outputs.extend(outputs.cpu().numpy())
#             all_answers.extend(answer.cpu().numpy())
#             # break
#         # outputs是模型根据测试集decode出来的问题
#         outputs = [tokenizer.decode(output_id, skip_special_tokens = True, clean_up_tokenization_spaces = True) for output_id in all_outputs]
#         # given_answer是测试集中的答案
#         given_answer = [data.vocab['answer_idx_to_token'][a] for a in all_answers]
#         # questions = [tokenizer.decode(source_id, skip_special_tokens = True, clean_up_tokenization_spaces = True) for source_id in all_answers]
#         # total = []
#         for a, output in tqdm(zip(given_answer, outputs)):  # 下面主体操作是根据decode出来的问题，模型来生成答案，然后和测试集原有答案进行计算准确率
#             # print(output)
#             chunks = output.split('<b>')
#             func_list = []
#             inputs_list = []
#             for chunk in chunks:
#                 # print(chunk)
#                 res = pattern.findall(chunk)
#                 # print(res)
#                 if len(res) == 0:
#                     continue
#                 res = res[0]
#                 func, inputs = res[0], res[1]
#                 if inputs == '':
#                     inputs = []
#                 else:
#                     inputs = inputs.split('<c>')

#                 func_list.append(func)
#                 inputs_list.append(inputs)
#             ans = executor.forward(func_list, inputs_list, ignore_error = True)
#             if ans == None:
#                 ans = 'no'
#             if ans == a:
#                 correct += 1
#             count += 1
#         acc = correct / count
#         logging.info('acc: {}'.format(acc))

#         return acc

def predict(args, kb, model, data, device, tokenizer, executor):
    model.eval()
    count, correct = 0, 0
    pattern = re.compile(r'(.*?)\((.*?)\)')
    with torch.no_grad():
        all_outputs = []
        for batch in tqdm(data, total=len(data)):
            source_ids = batch[0].to(device)
            outputs = model.generate(
                input_ids=source_ids,
                max_length=500,
            )

            all_outputs.extend(outputs.cpu().numpy())

        outputs = [tokenizer.decode(output_id, skip_special_tokens=True, clean_up_tokenization_spaces=True) for
                   output_id in all_outputs]

        # 获取ckpt_name
        # ckpt_name=str(args.ckpt).split('/')[-1]

        ckpt_name='teacher_ckpt'
        predict_file_name='predict-'+ckpt_name+'.txt'

        # 将预测出来的kopl进行记录
        predict_kopl_file_name='predict-kopl-'+ckpt_name+'.txt'
        with open(os.path.join(args.save_dir, predict_kopl_file_name), 'w') as f:
            for output in tqdm(outputs):
                f.write(output + '\n')

        with open(os.path.join(args.save_dir, predict_file_name), 'w') as f:
            for output in tqdm(outputs):
                chunks = output.split('<b>')
                func_list = []
                inputs_list = []
                for chunk in chunks:
                    # print(chunk)
                    res = pattern.findall(chunk)
                    # print(res)
                    if len(res) == 0:
                        continue
                    res = res[0]
                    func, inputs = res[0], res[1]
                    if inputs == '':
                        inputs = []
                    else:
                        inputs = inputs.split('<c>')

                    func_list.append(func)
                    inputs_list.append(inputs)
                ans = executor.forward(func_list, inputs_list, ignore_error=True)
                if ans == None:
                    ans = 'no'
                f.write(ans + '\n')
def validate_ddp(model, data, tokenizer,vocab, executor,epoch=1):
    print(f'model has module {hasattr(model, "module") }')
    model = model.module if hasattr(model, "module") else model
    model.eval()
    count, correct = 0, 0
    with torch.no_grad():
        all_outputs = []
        all_answers = []
        cnt=0
        for batch in tqdm(data, total=len(data)):
            # if (epoch<4 and cnt>3) or cnt>epoch*10000:
            #     break
            # cnt+=1
            # source_ids, source_mask, choices, target_ids, answer = [batch]
            source_ids, source_mask, choices, target_ids, answer = batch
            outputs = model.generate(
                input_ids=source_ids,
                max_length = 100,
                # decoder_start_token_id=tokenizer.lang_code_to_id["ro_RO"]
            )
            all_outputs.extend(outputs)
            all_answers.extend(target_ids)
        outputs = [tokenizer.decode(output_id, skip_special_tokens = True, clean_up_tokenization_spaces = True) for output_id in all_outputs]
        given_answer = [tokenizer.decode(a, skip_special_tokens = True, clean_up_tokenization_spaces = True) for a in all_answers]
        print(f"sourceid:{tokenizer.decode(source_ids[0],skip_special_tokens=False)}\
              \n outputid:{tokenizer.decode(all_outputs[0],skip_special_tokens=False)}\n =={outputs[0]}==>{given_answer[0]}")
        logging.info(f"sourceid:{tokenizer.decode(source_ids[0],skip_special_tokens=False)}\
              \n outputid:{tokenizer.decode(all_outputs[0],skip_special_tokens=False)}\n =={outputs[0]}==>{given_answer[0]}")
        # 创建进程池，根据需要设置进程数量
        # pool = mp.Pool(processes=4)
        # pool.join()
        for a, output in tqdm(zip(given_answer, outputs)):
            # chunks = output.split('<func>')
            # func_list = []
            # inputs_list = []
            # for chunk in chunks:
            #     chunk = chunk.strip()
            #     res = chunk.split('<arg>')
            #     res = [_.strip() for _ in res]
            #     if len(res) > 0:
            #         func = res[0]
            #         inputs = []
            #         if len(res) > 1:
            #             for x in res[1:]:
            #                 inputs.append(x)
            #         else:
            #             inputs = []
            #         func_list.append(func)
            #         inputs_list.append(inputs)
            # ans = executor.forward(func_list, inputs_list, ignore_error = True)
            ans=output
            if ans is None:
                ans = 'no'
            if isinstance(ans, list) and len(ans) > 0:
                ans = ans[0]
            if ans == a:
                correct += 1
            count += 1
        # correct = sum(results)
        # count = len(results)
        acc = correct / count
        logging.info('acc: {}'.format(acc))

        return acc

def validate_acc(args, kb, model, data, tokenizer, executor):
    model = model.module if hasattr(model, "module") else model
    model.eval()
    count, correct = 0, 0
    pattern = re.compile(r'(.*?)\((.*?)\)')
    with torch.no_grad():
        all_outputs = []
        all_answers = []
        for batch in tqdm(data, total=len(data)):
            source_ids, source_mask, choices, target_ids, answer = batch
            outputs = model.generate(
                input_ids=source_ids,
                max_length=100,
            )
            logging.info("answer:"+str(answer))
            all_outputs.extend(outputs)
            all_answers.extend(target_ids)
            # break
        # outputs是模型根据测试集decode出来的问题
        outputs = [tokenizer.decode(output_id, skip_special_tokens=True, clean_up_tokenization_spaces=True) for
                   output_id in all_outputs]
        given_answer = [tokenizer.decode(a, skip_special_tokens = True, clean_up_tokenization_spaces = True)for
                        a in all_answers]

        logging.info("outputs[0]"+ str(outputs[0]))
        logging.info("given_answer[0]"+str(given_answer[0]))
        # given_answer = [data.vocab['answer_idx_to_token'][a] for a in all_answers]
        # questions = [tokenizer.decode(source_id, skip_special_tokens = True, clean_up_tokenization_spaces = True) for source_id in all_answers]
        # total = []
        for a, output in tqdm(zip(given_answer, outputs)):  # 下面主体操作是根据decode出来的问题，模型来生成答案，然后和测试集原有答案进行计算准确率
            # print(output)
            # chunks = output.split('<b>')
            # func_list = []
            # inputs_list = []
            # for chunk in chunks:
            #     # print(chunk)
            #     res = pattern.findall(chunk)
            #     # print(res)
            #     if len(res) == 0:
            #         continue
            #     res = res[0]
            #     func, inputs = res[0], res[1]
            #     if inputs == '':
            #         inputs = []
            #     else:
            #         inputs = inputs.split('<c>')
            #
            #     func_list.append(func)
            #     inputs_list.append(inputs)
            # ans = executor.forward(func_list, inputs_list, ignore_error=True)

            ans=output
            if ans == None:
                ans = 'no'
            if ans == a:
                correct += 1
            count += 1
        acc = correct / count
        logging.info('acc: {}'.format(acc))

        return acc

# for 单机多卡
def validate(args, kb, model, data, tokenizer, executor):
    model.eval()
    count, correct = 0, 0
    pattern = re.compile(r'(.*?)\((.*?)\)')
    with torch.no_grad():
        all_outputs = []
        all_answers = []
        for batch in tqdm(data, total=len(data)):
            source_ids, source_mask, choices, target_ids, answer = [x.cuda() for x in batch]
            outputs = model.module.generate(
                input_ids=source_ids,
                max_length = 500,
            )

            all_outputs.extend(outputs.cpu().numpy())
            all_answers.extend(answer.cpu().numpy())
            # break
        # outputs是模型根据测试集decode出来的问题
        outputs = [tokenizer.decode(output_id, skip_special_tokens = True, clean_up_tokenization_spaces = True) for output_id in all_outputs]
        # given_answer是测试集中的答案
        given_answer = [data.vocab['answer_idx_to_token'][a] for a in all_answers]
        # questions = [tokenizer.decode(source_id, skip_special_tokens = True, clean_up_tokenization_spaces = True) for source_id in all_answers]
        # total = []
        for a, output in tqdm(zip(given_answer, outputs)):  # 下面主体操作是根据decode出来的问题，模型来生成答案，然后和测试集原有答案进行计算准确率
            # print(output)
            chunks = output.split('<b>')
            func_list = []
            inputs_list = []
            for chunk in chunks:
                # print(chunk)
                res = pattern.findall(chunk)
                # print(res)
                if len(res) == 0:
                    continue
                res = res[0]
                func, inputs = res[0], res[1]
                if inputs == '':
                    inputs = []
                else:
                    inputs = inputs.split('<c>')

                func_list.append(func)
                inputs_list.append(inputs)
            ans = executor.forward(func_list, inputs_list, ignore_error = True)

            if ans == None:
                ans = 'no'
            if ans == a:
                correct += 1
            count += 1
        acc = correct / count
        logging.info('acc: {}'.format(acc))

        return acc


def train(args):
    # device = 'cuda' if torch.cuda.is_available() else 'cpu'
    device = torch.device(args.gpu if args.use_cuda else "cpu")

    logging.info("Create train_loader and val_loader.........")
    vocab_json = os.path.join(args.input_dir, 'vocab.json')
    train_pt = os.path.join(args.input_dir, 'train.pt')
    val_pt = os.path.join(args.input_dir, 'test.pt')
    train_loader = DataLoader(vocab_json, train_pt, args.batch_size, training=True)
    val_loader = DataLoader(vocab_json, val_pt, args.batch_size)
    vocab = train_loader.vocab
    kb = DataForSPARQL(os.path.join(args.input_dir, 'kb.json'))
    logging.info("Create model.........")
    config_class, model_class, tokenizer_class = (BartConfig, BartForConditionalGeneration, BartTokenizer)
    tokenizer = tokenizer_class.from_pretrained(args.ckpt)
    model = model_class.from_pretrained(args.ckpt)
    model = model.to(device)
    logging.info(model)
    # rule_executor = RuleExecutor(vocab, os.path.join(args.input_dir, 'kb.json'))
    rule_executor = RuleExecutor(os.path.join(args.input_dir, 'kb.json'))
    # validate(args, kb, model, val_loader, device, tokenizer, rule_executor)
    predict(args, kb, model, val_loader, device, tokenizer, rule_executor)

    # vis(args, kb, model, val_loader, device, tokenizer)


def main():
    parser = argparse.ArgumentParser()
    # input and output
    parser.add_argument('--input_dir', default='./dataset/plus_subset/preprocessed_data')  # 调试的时候路径用一个点，在下方终端Bart_Program下运行用两个点，对于这个项目要想统一，看should_read.md文件
    parser.add_argument('--save_dir', default='./output/single_teacher_dcs/predict_result', help='path to save checkpoints and logs')
    # parser.add_argument('--model_name_or_path', default='./model/bart-kopl')
    parser.add_argument('--ckpt',  default='./output/single_teacher_dcs/checkpoint/checkpoint-81189')

    # training parameters
    parser.add_argument('--batch_size', default=256, type=int)
    parser.add_argument('--seed', type=int, default=666, help='random seed')

    # validating parameters
    # parser.add_argument('--num_return_sequences', default=1, type=int)
    # parser.add_argument('--top_p', default=)
    # model hyperparameters
    parser.add_argument('--dim_hidden', default=1024, type=int)
    parser.add_argument('--alpha', default = 1e-4, type = float)

    parser.add_argument('--use_cuda', type=bool, default=True)
    parser.add_argument('--gpu', type=int, default=1)
    # os.environ["CUDA_VISIBLE_DEVICES"]="6"

    args = parser.parse_args()

    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)
    time_ = time.strftime("%Y-%m-%d-%H:%M:%S", time.localtime())
    fileHandler = logging.FileHandler(os.path.join(args.save_dir, '{}.predict.log'.format(time_)))
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)
    # args display
    for k, v in vars(args).items():
        logging.info(k+':'+str(v))

    seed_everything(666)

    train(args)


if __name__ == '__main__':
    main()


