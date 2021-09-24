""" This file is for training original model without routing modules.
"""
from __future__ import print_function

import torch
import torch.nn as nn
import torch.backends.cudnn as cudnn
from torch.autograd import Variable

import os
import shutil
import argparse
import time
import logging

import models
from data import *
import torch.nn.functional as F
from torch.autograd import Variable
import models
from data import *
from util_adv import pgd_main, pgd_avg, pgd_max, pgd_k
import torch.nn.functional as F
import torch.nn as nn
import numpy as np

n_branch = 3
model_names = sorted(name for name in models.__dict__
                     if name.islower() and not name.startswith('__')
                     and callable(models.__dict__[name])
                     )

def path_check(string): #checks for valid path
    if os.path.exists(string):
        return string
    else:
        raise FileNotFoundError(string)
print('3')

def parse_args():
    # hyper-parameters are from ResNet paper
    parser = argparse.ArgumentParser(description='PyTorch MNIST training')
    


    parser.add_argument('--model',choices=['brn','lenet'],
                        help='choose the model')
    parser.add_argument('--trained_path', type=path_check,
                        help='path to trained model')
    parser.add_argument('--save_name', type=str,
                        help='path to trained model')


    '''
    parser.add_argument('cmd', choices=['train', 'test'])
    parser.add_argument('arch', metavar='ARCH', default='mnist_smallcnn',
                        choices=model_names,
                        help='model architecture: ' +
                             ' | '.join(model_names) +
                             ' (default: mnist_smallcnn)')
    parser.add_argument('--dataset', '-d', type=str, default='MNIST',
                        choices=['MNIST'],
                        help='dataset choice')
    parser.add_argument('--workers', default=8, type=int, metavar='N',
                        help='number of data loading workers (default: 4 )')
    parser.add_argument('--iters', default=13100, type=int,
                        help='number of total iterations (default: 13100)')
    parser.add_argument('--start-iter', default=0, type=int,
                        help='manual iter number (useful on restarts)')
    parser.add_argument('--batch-size', default=256, type=int,
                        help='mini-batch size (default: 256)')
    parser.add_argument('--lr', default=0.033, type=float,
                        help='initial learning rate')
    parser.add_argument('--momentum', default=0.9, type=float,
                        help='momentum')
    parser.add_argument('--weight-decay', default=5e-4, type=float,
                        help='weight decay (default: 5e-4)')
    parser.add_argument('--print-freq', default=10, type=int,
                        help='print frequency (default: 10)')
    parser.add_argument('--resume', default='', type=str,
                        help='path to  latest checkpoint (default: None)')
    parser.add_argument('--pretrained', dest='pretrained', action='store_true',
                        help='use pretrained model')
    parser.add_argument('--step-ratio', default=0.1, type=float,
                        help='ratio for learning rate deduction')
    parser.add_argument('--warm-up', action='store_true',
                        help='for n = 18, the model needs to warm up for 400 '
                             'iterations')
    parser.add_argument('--save-folder', default='save_checkpoints/', type=str,
                        help='folder to save the checkpoints')
    parser.add_argument('--eval-every', default=100, type=int,
                        help='evaluate model every (default: 100) iterations')

    ## adverserial parameters
    parser.add_argument('--attack_algo', default='ifgm', help='adversarial algorithm')
    parser.add_argument('--attack_eps', type=float, default=0.3, help='perturbation radius for attack phase')
    parser.add_argument('--attack_gamma', type=float, default=0.01, help='step size for adv training')
    parser.add_argument('--attack_adv_iter', type=int, default=40,  help='how many epochs to wait before another test')
    parser.add_argument('--attack_randinit', type=bool, default=True, help="randinit flag for attack algo")
    parser.add_argument('--defend_algo', default='ifgm', help='adversarial algorithm')
    parser.add_argument('--defend_eps', type=float, default=0.3, help='perturbation radius for defend phase')
    parser.add_argument('--defend_gamma', type=float, default=0.01, help='perturbation radius for defend phase')
    parser.add_argument('--defend_adv_iter', type=int, default=40,  help='how many epochs to wait before another test')
    parser.add_argument('--defend_randinit', type=bool, default=True, help="randinit flag for defend algo")
    '''
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    save_path = args.save_path = os.path.join(args.save_folder, args.arch)
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # config logging file
    args.logger_file = os.path.join(save_path, 'log_{}.txt'.format(args.cmd))
    handlers = [logging.FileHandler(args.logger_file, mode='w'),
                logging.StreamHandler()]
    logging.basicConfig(level=logging.INFO,
                        datefmt='%m-%d-%y %H:%M',
                        format='%(asctime)s:%(message)s',
                        handlers=handlers)

    if args.cmd == 'train':
        logging.info('start training {}'.format(args.arch))
        run_training(args)

    elif args.cmd == 'test':
        logging.info('start evaluating {} with checkpoints from {}'.format(
            args.arch, args.resume))
        test_model(args)


def run_training(args):
    # create model
    model = models.__dict__[args.arch](args.pretrained)
    #model = torch.nn.DataParallel(model).cuda()

    best_prec1 = 0
    # optionally resume from a checkpoint
    if args.resume:
        if os.path.isfile(args.resume):
            logging.info('=> loading checkpoint `{}`'.format(args.resume))
            checkpoint = torch.load(args.resume)
            args.start_iter = checkpoint['iter']
            best_prec1 = checkpoint['best_prec1']
            model.load_state_dict(checkpoint['state_dict'])
            logging.info('=> loaded checkpoint `{}` (iter: {})'.format(
                args.resume, checkpoint['iter']
            ))
        else:
            logging.info('=> no checkpoint found at `{}`'.format(args.resume))

    #cudnn.benchmark = False

    train_loader = prepare_train_data(dataset=args.dataset,
                                      batch_size=args.batch_size,
                                      shuffle=True,
                                      num_workers=args.workers)
    test_loader = prepare_test_data(dataset=args.dataset,
                                    batch_size=args.batch_size,
                                    shuffle=False,
                                    num_workers=args.workers)

    # define loss function (criterion) and optimizer


    train_criterion = nn.CrossEntropyLoss()
#.cuda()
    criterion = nn.CrossEntropyLoss()
#.cuda()

    optimizer = torch.optim.SGD(model.parameters(), args.lr,
                                momentum=args.momentum,
                                weight_decay=args.weight_decay)

    batch_time = AverageMeter()
    data_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()
    top1_list = []
    for idx in range(n_branch):
        top1_list.append(AverageMeter())

    end = time.time()

    #prec1 = validate(args, test_loader, model, criterion)
    if args.defend_algo == 'pgd_main':
        defend_algo = pgd_main
    elif args.defend_algo == 'pgd_avg':
        defend_algo = pdg_avg
    elif args.defend_algo == 'pgd_max':
        defend_algo = pgd_max
    elif args.defend_algo == 'None':
        defend_algo = None
    else:
        raise NotImplementedError


    # adversarial algorithm
    if args.attack_algo == 'pgd_main':
        attack_algo = pgd_main
    elif args.attack_algo == 'pgd_avg':
        attack_algo = pgd_avg
    elif args.attack_algo == 'pgd_max':
        attack_algo = pgd_max
    elif args.attack_algo == 'None':
        attack_algo = None
    else:
        raise NotImplementedError



    for i in range(args.start_iter, args.iters):
        model.train()
        adjust_learning_rate(args, optimizer, i)

        input, target = next(iter(train_loader))
        # measuring data loading time
        data_time.update(time.time() - end)
        target = target.squeeze().long()
#.cuda(async=True)
        target_var = Variable(target)
        if defend_algo:
            input_adv = defend_algo(input, None, F.cross_entropy,
                y=target_var,
                eps=args.defend_eps,
                model=model,
                steps=args.defend_adv_iter,
                gamma=args.defend_gamma,
                randinit=args.defend_randinit).data
            input_adv_var = Variable(input_adv)
        input_var = Variable(input)


        # compute output
        if defend_algo: 
            output_branch = model(input_var)
            loss = 0
            for idx in range(len(output_branch)):
                loss += train_criterion(output_branch[idx], target_var) * 0.5
            output_adv_branch = model(input_adv_var)
            for idx in range(len(output_adv_branch)):
                loss += train_criterion(output_adv_branch[idx], target_var) * 0.5
        else:
            output_branch = model(input_var)
            loss = 0
            for idx in range(len(output_branch)):
                loss += train_criterion(output_branch[idx], target_var)






        # measure accuracy and record loss
        losses.update(loss.item(), input.size(0))
        for idx in range(len(output_branch)):
            prec1_branch = accuracy(output_branch[idx].data, target, topk=(1,))
            top1_list[idx].update(prec1_branch[0].item(), input.size(0)) 

        # compute gradient and do SGD step
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        # measure elapsed time
        batch_time.update(time.time() - end)
        end = time.time()

        # print log
        if i % args.print_freq == 0 or i == (args.iters - 1):
            logging.info("Iter: [{0}/{1}]\t"
                         "Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t"
                         "Data {data_time.val:.3f} ({data_time.avg:.3f})\t"
                         "Loss {loss.val:.3f} ({loss.avg:.3f})\t"
                         "Prec_B1@1 {top1_b1.val:.3f} ({top1_b1.avg:.3f})\t"
                         "Prec_B2@1 {top1_b2.val:.3f} ({top1_b2.avg:.3f})\t"
                         "Prec_Main@1 {top1_main.val:.3f} ({top1_main.avg:.3f})\t"
                          .format(
                            i,
                            args.iters,
                            batch_time=batch_time,
                            data_time=data_time,
                            loss=losses,
                            top1_b1=top1_list[0],
                            top1_b2=top1_list[1],
                            top1_main=top1_list[-1],
                                     )
            )

            # evaluate every 1000 steps
        if (i % args.eval_every == 0 and i > 0) or (i == args.iters - 1):
            prec1 = validate(args, test_loader, model, criterion)
            if attack_algo:
                _ = validate_adv(args, test_loader, model, criterion, attack_algo)
            is_best = prec1 > best_prec1
            best_prec1 = max(prec1, best_prec1)
            checkpoint_path = os.path.join(args.save_path,
                                           'checkpoint_{:05d}.pth.tar'.format(
                                               i))
            save_checkpoint({
                'iter': i,
                'arch': args.arch,
                'state_dict': model.state_dict(),
                'best_prec1': best_prec1,
            },
                is_best, filename=checkpoint_path)
            shutil.copyfile(checkpoint_path, os.path.join(args.save_path,
                                                          'checkpoint_latest'
                                                          '.pth.tar'))

def validate(args, test_loader, model, criterion):
    batch_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()
    top1_list = []

    for idx in range(n_branch):
        top1_list.append(AverageMeter())

    # switch to evaluation mode
    model.eval()
    end = time.time()
    for i, (input, target) in enumerate(test_loader):
        target = target.squeeze().long()
#.cuda(async=True)
        input_var = Variable(input, volatile=True)
        target_var = Variable(target, volatile=True)

        # compute output
        output_branch = model(input_var)
        loss = 0
        for idx in range(len(output_branch)):
            loss = loss + criterion(output_branch[idx], target_var)

        # measure accuracy and record loss
        for idx in range(len(output_branch)):
            prec1_branch, = accuracy(output_branch[idx].data, target, topk=(1,))
            top1_list[idx].update(prec1_branch, input.size(0)) 
        losses.update(loss.item(), input.size(0))
        batch_time.update(time.time() - end)
        end = time.time()

        if i % args.print_freq == 0 or (i == (len(test_loader) - 1)):
            logging.info(
                'Test: [{}/{}]\t'
                'Time: {batch_time.val:.4f}({batch_time.avg:.4f})\t'
                'Loss: {loss.val:.3f}({loss.avg:.3f})\t'
                "Prec_B1@1 {top1_b1.val:.3f} ({top1_b1.avg:.3f})\t"
                "Prec_B2@1 {top1_b2.val:.3f} ({top1_b2.avg:.3f})\t"
                "Prec_Main@1 {top1_main.val:.3f} ({top1_main.avg:.3f})\t"
                .format(
                    i, len(test_loader), batch_time=batch_time,
                    loss=losses,
                    top1_b1=top1_list[0],
                    top1_b2=top1_list[1],
                    top1_main=top1_list[-1],
                )
            )

    logging.info(' * Prec_Main@1 {top1_main.avg:.3f}\t' 
    ' * Prec_B1@1 {top1_b1.avg:.3f}\t'  
    ' * Prec_B2@1 {top1_b2.avg:.3f}\t'  
    'Loss {loss.avg:.3f}\t'
    .format(
        top1_main=top1_list[-1], 
        top1_b1=top1_list[0],
        top1_b2=top1_list[1],
        loss=losses))
    return top1.avg


def validate_adv(args, test_loader, model, criterion, attack_algo):
    batch_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()
    top1_list = []
    for idx in range(n_branch):
        top1_list.append(AverageMeter())

    # switch to evaluation mode
    model.eval()
    end = time.time()
    for i, (input, target) in enumerate(test_loader):
        target = target.squeeze().long()
#.cuda(async=True)
        target_var = Variable(target, volatile=True)
        input_adv = attack_algo(input, None, F.cross_entropy,
            y=target_var,
            eps=args.attack_eps,
            model=model,
            steps=args.attack_adv_iter,
            gamma=args.attack_gamma,
            randinit=args.attack_randinit).data
        input_var = Variable(input_adv, volatile=True)

        # compute output
        output_branch = model(input_var)
        loss = 0
        for idx in range(len(output_branch)):
            loss = loss + criterion(output_branch[idx], target_var)

        # measure accuracy and record loss
        for idx in range(len(output_branch)):
            prec1_branch, = accuracy(output_branch[idx].data, target, topk=(1,))
            top1_list[idx].update(prec1_branch, input.size(0)) 
        losses.update(loss.item(), input.size(0))
        batch_time.update(time.time() - end)
        end = time.time()

        if i % args.print_freq == 0 or (i == (len(test_loader) - 1)):
            logging.info(
                'Test: [{}/{}]\t'
                'Time: {batch_time.val:.4f}({batch_time.avg:.4f})\t'
                'Loss: {loss.val:.3f}({loss.avg:.3f})\t'
                "Adv Prec_B1@1 {top1_b1.val:.3f} ({top1_b1.avg:.3f})\t"
                "Adv Prec_B2@1 {top1_b2.val:.3f} ({top1_b2.avg:.3f})\t"
                "Adv Prec_Main@1 {top1_main.val:.3f} ({top1_main.avg:.3f})\t"
                .format(
                    i, len(test_loader), batch_time=batch_time,
                    loss=losses,
                    top1_b1=top1_list[0],
                    top1_b2=top1_list[1],
                    top1_b3=top1_list[2],
                    top1_main=top1_list[-1],
                )
            )

    logging.info(' * Prec_Main@1 {top1.avg:.3f}\t' 
    ' * Prec_B1@1 {top1_b1.avg:.3f}\t'  
    ' * Prec_B2@1 {top1_b2.avg:.3f}\t'  
    'Loss {loss.avg:.3f}\t'
    .format(
        top1=top1_list[-1], 
        top1_b1=top1_list[0],
        top1_b2=top1_list[1],
        loss=losses))
    return top1.avg



def validate_one_adv(args, test_loader, model, criterion, attack_algo, T, K=0, flop_table=None):
    batch_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()
    exit_b1 = AverageMeter()
    exit_b2 = AverageMeter()
    exit_m = AverageMeter()

    # switch to evaluation mode
    model.eval()
    end = time.time()
    for i, (input, target) in enumerate(test_loader):
        target = target.squeeze().long()
#.cuda(async=True)
        target_var = Variable(target, volatile=True)
        input_adv = attack_algo(input, None, F.cross_entropy,
            y=target_var,
            eps=args.attack_eps,
            model=model,
            steps=args.attack_adv_iter,
            gamma=args.attack_gamma,
            randinit=args.attack_randinit,
            branch_num=K).data
        input_var = Variable(input_adv, volatile=True)

        # compute output
        output_branch = model(input_var)
        
        ## dynamic inference
        sm = nn.functional.softmax
        prob_branch1 = sm(output_branch[0])
        prob_branch2 = sm(output_branch[1])
        prob_main = sm(output_branch[2])

        measure_branch1 = torch.sum(torch.mul(-prob_branch1, torch.log(prob_branch1 + 1e-5)), dim=1)
        measure_branch2 = torch.sum(torch.mul(-prob_branch2, torch.log(prob_branch2 + 1e-5)), dim=1)
        measure_main = torch.sum(torch.mul(-prob_main, torch.log(prob_main + 1e-5)), dim=1)


        for j in range(input.size(0)):
            tar = torch.from_numpy(target[j].cpu().numpy().reshape((-1,1))).squeeze(0).long()
#.cuda(async=True)
            tar_var = Variable(torch.from_numpy(target_var.data.cpu().numpy()[j].flatten()).long())
#.cuda())

            if (measure_branch1.data).cpu().numpy()[j] < T[0] :
                out = Variable(torch.from_numpy(output_branch[0].data.cpu().numpy()[j].reshape((1,-1))).float())
#.cuda())
                loss = criterion(out, tar_var)
                prec1, = accuracy(out.data, tar, topk=(1,))
                top1.update(prec1, 1)
                losses.update(loss.item(), 1)
                exit_b1.update(1, 1)
                exit_b2.update(0, 1)
                exit_m.update(0,1)
    
            elif (measure_branch2.data).cpu().numpy()[j] < T[1] :
                out = Variable(torch.from_numpy(output_branch[1].data.cpu().numpy()[j].reshape((1,-1))).float())
#.cuda())
                loss = criterion(out, tar_var)
                prec1, = accuracy(out.data, tar, topk=(1,))
                top1.update(prec1, 1)
                losses.update(loss.item(), 1)
                exit_b1.update(0, 1)
                exit_b2.update(1, 1)
                exit_m.update(0,1)
    
            else:
                out = Variable(torch.from_numpy(output_branch[2].data.cpu().numpy()[j].reshape((1,-1))).float())
#.cuda())
                loss = criterion(out, tar_var)
                prec1, = accuracy(out.data, tar, topk=(1,))
                top1.update(prec1, 1)
                losses.update(loss.item(), 1)
                exit_b1.update(0, 1)
                exit_b2.update(0, 1)
                exit_m.update(1,1)


        batch_time.update(time.time() - end)
        end = time.time()

        if (i % args.print_freq == 0) or (i == len(test_loader) - 1):
            logging.info(
                'Test: [{}/{}]\t'
                'Time: {batch_time.val:.4f}({batch_time.avg:.4f})\t'
                'Loss: {loss.val:.3f}({loss.avg:.3f})\t'
                'Prec@1: {top1.val:.3f}({top1.avg:.3f})\t'.format(
                    i, len(test_loader), batch_time=batch_time,
                    loss=losses, top1=top1
                )
            )

            print(
                'Test: [{}/{}]\t'
                'Time: {batch_time.val:.4f}({batch_time.avg:.4f})\t'
                'Loss: {loss.val:.3f}({loss.avg:.3f})\t'
                'Exit_branch1 {exit_b1.val:.4f} ({exit_b1.avg:.4f})\t'
                'Exit_branch2 {exit_b2.val:.4f} ({exit_b2.avg:.4f})\t'
                'Exit_main {exit_m.val:.3f} ({exit_m.avg:.3f})\t'
                'Prec@1: {top1.val:.3f}({top1.avg:.3f})\t'.format(
                    i, len(test_loader), batch_time=batch_time,
                    loss=losses,exit_b1=exit_b1, exit_b2=exit_b2,
                    exit_m=exit_m, top1=top1
                )
            )
    exit_table = [exit_b1.avg, exit_b2.avg, exit_m.avg]
    flops = sum([a*b for a,b in zip(exit_table,flop_table)])
    logging.info(' * Prec@1 {top1.avg:.3f}'.format(top1=top1))
    print(' * Prec@1 {top1.avg:.3f}'.format(top1=top1))
    print(' * MFlops {flops:.2f}'.format(flops=flops))
    return top1.avg



def validate_one(args, test_loader, model, criterion, T, flop_table):
    batch_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()
    exit_b1 = AverageMeter()
    exit_b2 = AverageMeter()
    exit_m = AverageMeter()

    # switch to evaluation mode
    model.eval()
    end = time.time()

    
    for i, (input, target) in enumerate(test_loader):

        target = target.squeeze().long()
#.cuda(async=True)
        target_var = Variable(target, volatile=True)
        input_var = Variable(input, volatile=True)


        # compute output
        output_branch = model(input_var)
        
        ## dtnamic inference
        sm = nn.functional.softmax
        prob_branch1 = sm(output_branch[0])
        prob_branch2 = sm(output_branch[1])
        prob_main = sm(output_branch[2])

        measure_branch1 = torch.sum(torch.mul(-prob_branch1, torch.log(prob_branch1 + 1e-5)), dim=1)
        measure_branch2 = torch.sum(torch.mul(-prob_branch2, torch.log(prob_branch2 + 1e-5)), dim=1)
        measure_main = torch.sum(torch.mul(-prob_main, torch.log(prob_main + 1e-5)), dim=1)
            
               
        for j in range(input.size(0)):
            tar = torch.from_numpy(target[j].cpu().numpy().reshape((-1,1))).squeeze(0).long()
#.cuda(async=True)
            tar_var = Variable(torch.from_numpy(target_var.data.cpu().numpy()[j].flatten()).long())
#.cuda())
            if (measure_branch1.data).cpu().numpy()[j] < T[0] :
                out = Variable(torch.from_numpy(output_branch[0].data.cpu().numpy()[j].reshape((1,-1))).float())
#.cuda())
                loss = criterion(out, tar_var)
                prec1, = accuracy(out.data, tar, topk=(1,))
                top1.update(prec1, 1)
                losses.update(loss.item(), 1)
                exit_b1.update(1, 1)
                exit_b2.update(0, 1)
                exit_m.update(0,1)
    
            elif (measure_branch2.data).cpu().numpy()[j] < T[1] :
                out = Variable(torch.from_numpy(output_branch[1].data.cpu().numpy()[j].reshape((1,-1))).float())
#.cuda())
                loss = criterion(out, tar_var)
                prec1, = accuracy(out.data, tar, topk=(1,))
                top1.update(prec1, 1)
                losses.update(loss.item(), 1)
                exit_b1.update(0, 1)
                exit_b2.update(1, 1)
                exit_m.update(0,1)
    
            else:
                out = Variable(torch.from_numpy(output_branch[2].data.cpu().numpy()[j].reshape((1,-1))).float())
#.cuda())
                loss = criterion(out, tar_var)
                prec1, = accuracy(out.data, tar, topk=(1,))
                top1.update(prec1, 1)
                losses.update(loss.item(), 1)
                exit_b1.update(0, 1)
                exit_b2.update(0, 1)
                exit_m.update(1,1)

        batch_time.update(time.time() - end)
        end = time.time()

        if (i % args.print_freq == 0) or (i == len(test_loader) - 1):
            logging.info(
                'Test: [{}/{}]\t'
                'Time: {batch_time.val:.4f}({batch_time.avg:.4f})\t'
                'Loss: {loss.val:.3f}({loss.avg:.3f})\t'
                'Prec@1: {top1.val:.3f}({top1.avg:.3f})\t'.format(
                    i, len(test_loader), batch_time=batch_time,
                    loss=losses, top1=top1
                )
            )

            print(
                'Test: [{}/{}]\t'
                'Time: {batch_time.val:.4f}({batch_time.avg:.4f})\t'
                'Loss: {loss.val:.3f}({loss.avg:.3f})\t'
                'Exit_branch1 {exit_b1.val:.4f} ({exit_b1.avg:.4f})\t'
                'Exit_branch2 {exit_b2.val:.4f} ({exit_b2.avg:.4f})\t'
                'Exit_main {exit_m.val:.3f} ({exit_m.avg:.3f})\t'
                'Prec@1: {top1.val:.3f}({top1.avg:.3f})\t'.format(
                    i, len(test_loader), batch_time=batch_time,
                    loss=losses,exit_b1=exit_b1, exit_b2=exit_b2,
                    exit_m=exit_m, top1=top1
                )
            )
    exit_table = [exit_b1.avg, exit_b2.avg, exit_m.avg]
    flops = sum([a*b for a,b in zip(exit_table,flop_table)])
    logging.info(' * Prec@1 {top1.avg:.3f}'.format(top1=top1))
    print(' * Prec@1 {top1.avg:.3f}'.format(top1=top1))
    print(' * MFlops {flops:.2f}'.format(flops=flops))
    return top1.avg







def get_msd_T(args, test_loader, model, criterion):
    batch_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()

    model.eval()
    end = time.time()
    b1 = []
    b2 = []

    index = 0   
    for i, (input, target) in enumerate(test_loader):

        target = target.squeeze().long()
#.cuda(async=True)
        target_var = Variable(target, volatile=True)
        input_var = Variable(input, volatile=True)


        # compute output
        output_branch = model(input_var)
        
        ## dtnamic inference
        sm = nn.functional.softmax
        prob_branch1 = sm(output_branch[0])
        prob_branch2 = sm(output_branch[1])
        prob_main = sm(output_branch[2])

        measure_branch1 = torch.sum(torch.mul(-prob_branch1, torch.log(prob_branch1 + 1e-5)), dim=1)
        measure_branch2 = torch.sum(torch.mul(-prob_branch2, torch.log(prob_branch2 + 1e-5)), dim=1)
        measure_main = torch.sum(torch.mul(-prob_main, torch.log(prob_main + 1e-5)), dim=1)

        for j in range(0, input.size(0)):
             b1.append((index, measure_branch1.data.cpu().numpy()[j]))
             b2.append((index, measure_branch2.data.cpu().numpy()[j]))
             index += 1


    data_len = len(b1)
    remove_idx = []
    T = []

    b1 = sorted(b1, key=lambda tuple:tuple[1])
    T.append(b1[int(data_len * 1.0 / 3.0)][1])
    remove_idx.extend([x[0] for x in b1[0:int(data_len * 1.0 / 3.0)]])

    b2 = [x for x in b2 if x[0] not in remove_idx]
    b2 = sorted(b2, key=lambda tuple:tuple[1])
    T.append(b2[int(data_len * 1.0 / 3.0)][1])
    remove_idx.extend([x[0] for x in b2[0:int(data_len * 1.0 / 3.0)]])

    return T




def test_model(args):
    # create model
    model = models.__dict__[args.arch](args.pretrained)
    #model = torch.nn.DataParallel(model).cuda()

    if args.resume:
        if os.path.isfile(args.resume):
            logging.info('=> loading checkpoint `{}`'.format(args.resume))
            checkpoint = torch.load(args.resume)
            args.start_iter = checkpoint['iter']
            best_prec1 = checkpoint['best_prec1']
            model.load_state_dict(checkpoint['state_dict'])
            logging.info('=> loaded checkpoint `{}` (iter: {})'.format(
                args.resume, checkpoint['iter']
            ))
        else:
            logging.info('=> no checkpoint found at `{}`'.format(args.resume))

    #cudnn.benchmark = False
    test_dp_loader = prepare_test_data(dataset=args.dataset,
                                    batch_size=args.batch_size,
                                    shuffle=False,
                                    num_workers=args.workers)
    criterion = nn.CrossEntropyLoss()
#.cuda()


    T = get_msd_T(args, test_dp_loader, model, criterion)
    T[0] = T[0]  * 3
    T[1] = T[1]  * 4


    flop_table = [0.818, 7.00, 9.25]

    validate_one(args, test_dp_loader, model, criterion,  T, flop_table=flop_table)
    

    for k in range(n_branch):
        if k != 2:
            print('Eval on Branch' + str(k+1) + ' Attack')
        else:
            print('Eval on Main Branch Attack')
        validate_one_adv(args, test_dp_loader, model, criterion, pgd_k, T, k, flop_table=flop_table)


    print('Eval on Average Attack')
    validate_one_adv(args, test_dp_loader, model, criterion, pgd_avg, T, flop_table=flop_table)

    print('Eval on Max Attack')
    validate_one_adv(args, test_dp_loader, model, criterion, pgd_max, T, flop_table=flop_table)
    

def save_checkpoint(state, is_best, filename='checkpoint.pth.tar'):
    torch.save(state, filename)
    if is_best:
        save_path = os.path.dirname(filename)
        shutil.copyfile(filename, os.path.join(save_path,
                                               'model_best.pth.tar'))


class AverageMeter(object):
    """Computes and stores the average and current value"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def adjust_learning_rate(args, optimizer, _iter):
    """divide lr by 10 at 117k and 129k """
    if args.warm_up and (_iter < 400):
        lr = 0.01
    elif 11700 <= _iter < 12900:
        lr = args.lr * (args.step_ratio ** 1)
    elif _iter >= 12900:
        lr = args.lr * (args.step_ratio ** 2)
    else:
        lr = args.lr

    if _iter % args.eval_every == 0:
        logging.info('Iter [{}] learning rate = {}'.format(_iter, lr))

    for param_group in optimizer.param_groups:
        param_group['lr'] = lr



def accuracy(output, target, topk=(1,)):
    """Computes the precision@k for the specified values of k"""
    maxk = max(topk)
    batch_size = target.size(0)

    _, pred = output.topk(maxk, 1, True, True)
    pred = pred.t()
    correct = pred.eq(target.view(1, -1).expand_as(pred))

    res = []
    for k in topk:
        correct_k = correct[:k].view(-1).float().sum(0)
        res.append(correct_k.mul_(100.0 / batch_size))
    return res



if __name__ == '__main__':
    main()
