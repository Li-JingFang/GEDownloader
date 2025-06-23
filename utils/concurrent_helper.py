import logging
import time
import traceback
import queue as Q
from collections import OrderedDict
from multiprocessing import Process, Queue
from concurrent import futures


def _run_func_and_time_it(func, *args):
    s = time.time()

    try:
        rtv = func(*args)
    except Exception as e:
        traceback.print_exc()
        logging.error(str(traceback.format_exc()))
        raise

    e = time.time()
    return e - s, rtv


def independent_process_wrap(func, idx, queue_rtv, *args):
    try:
        rtv = func(*args)
    except Exception as e:
        rtv = (-1, e)

    queue_rtv.put((idx, rtv))


class IndependentExecutor(object):
    def __init__(self, max_workers=1):
        self.max_workers = max_workers
        self.finished_num = 0
        self.todo = []
        self.all_tasks = []
        self.queue_rtv = Queue()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        pass

    def submit(self, func, *args, **kwargs):
        future = IndependentFuture(
            func, len(self.all_tasks), self.queue_rtv, *args, **kwargs
        )
        self.todo.append(future)
        self.all_tasks.append(future)
        return future


class IndependentFuture(object):
    def __init__(self, func, index, queue_rtv, *args, **kwargs):
        self.p = Process(
            target=independent_process_wrap,
            args=((func, index, queue_rtv) + args),
            kwargs=kwargs,
        )
        self.index = index
        self.rtv = None

    def result(self):
        if isinstance(self.rtv, Exception):
            return self.rtv
        else:
            return self.rtv


def check_independent_future_as_completed(todo, executor):
    for i in range(executor.max_workers):
        if executor.todo:
            future = executor.todo.pop(0)
            future.p.start()

    while True:
        if executor.finished_num >= len(executor.all_tasks):
            raise StopIteration()

        idx, rtv = executor.queue_rtv.get()
        finished_future = executor.all_tasks[idx]
        finished_future.p.join()
        del finished_future.p
        finished_future.rtv = rtv
        executor.finished_num += 1

        if executor.todo:
            next_future = executor.todo.pop(0)
            next_future.p.start()

        yield finished_future


class _SingleExecutor(object):
    def __init__(self, max_workers=1):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        pass

    def submit(self, func, *args, **kwargs):
        return _SingleFuture(func, *args, **kwargs)


class _SingleFuture(object):
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def result(self):
        return self.func(*self.args, **self.kwargs)


def _check_as_compeleted(todo, concurrent_type, executor):
    if concurrent_type == "single":
        for future in todo:
            yield future
    elif concurrent_type == "independent-process":
        for future in check_independent_future_as_completed(todo, executor):
            yield future
    else:
        for rtv in futures.as_completed(todo):
            yield rtv


def run_with_concurrent(
        func,
        args_list,
        concurrent_type="thread",  # ["single", "thread", "process", "independent-process"]
        concurrent_num=1,
        show_process="",  # ["", "tqdm", "print"]
        raise_exception=True,
):
    if not args_list:
        return []

    if concurrent_type == "thread":
        concurrent_executor = futures.ThreadPoolExecutor
    elif concurrent_type == "process":
        concurrent_executor = futures.ProcessPoolExecutor
    elif concurrent_type == "independent-process":
        concurrent_executor = IndependentExecutor
    elif concurrent_type == "single":
        concurrent_executor = _SingleExecutor
    else:
        raise ValueError("unknow concurrent type, {}".format(concurrent_type))

    start_time = time.time()
    rtv = [None] * len(args_list)

    with concurrent_executor(max_workers=concurrent_num) as executor:
        to_do = OrderedDict()
        for idx, args in enumerate(args_list):
            if type(args) not in (tuple, list):
                args = (args,)
            to_do[executor.submit(_run_func_and_time_it, func, *args)] = idx

        for fns_idx, future in enumerate(
                _check_as_compeleted(to_do, concurrent_type, executor), 1
        ):
            used_time = -1

            try:
                used_time, real_rtv = future.result()
                rtv[to_do[future]] = real_rtv
            except Exception as e:
                rtv[to_do[future]] = e
                if raise_exception:
                    raise

            if show_process == "print":
                print(
                    "[{:>5}/{:<5}] ...... Run {} with {} ...... in {:>10.4f} seconds.".format(
                        fns_idx,
                        len(args_list),
                        func.__name__,
                        concurrent_type,
                        used_time,
                    )
                )

    if show_process == "print":
        time_used = time.time() - start_time
        if time_used <= 100:
            time_str = "{:>10.4f} seconds".format(time_used)
        else:
            time_str = "{:>10.4f} minutes".format(time_used / 60.0)

        print(
            ">>>>>> Run {} with {} total use {}.".format(
                func.__name__, concurrent_type, time_str
            )
        )

    return rtv


def _run_with_mq_wrap(init_func, init_args, func, task_q):
    if type(init_args) not in (tuple, list):
        init_args = (init_args,)

    init_func(*init_args)
    rtv_dict = {}

    while True:
        if task_q.qsize() == 0:
            break

        try:
            idx, args = task_q.get(timeout=2)
        except Q.Empty as _:
            break

        try:
            rtv = func(*args)
            rtv_dict[idx] = rtv
        except Exception as e:
            logging.error(str(traceback.format_exc()))
            rtv_dict[idx] = e

    return rtv_dict


def run_with_message_queue(
        init_func,
        init_args_list,
        func,
        args_list,
        concurrent_type="independent-process",  # support "single","thread","independent-process"
        show_process="",  # support ["", "tqdm", "print"]
        raise_exception=True,
):
    if concurrent_type not in ("single", "thread", "independent-process"):
        raise ValueError("not support concurrent type in run_with_mq")

    task_q = Queue()
    for idx, args in enumerate(args_list):
        task_q.put((idx, args))

    concurrent_num = len(init_args_list)
    rtvs = run_with_concurrent(
        _run_with_mq_wrap,
        [(init_func, init_args_list[i], func, task_q) for i in range(concurrent_num)],
        concurrent_type,
        concurrent_num,
        show_process,
        raise_exception,
    )

    total_rtvs = [None] * len(args_list)
    for d in rtvs:
        for k, v in d.items():
            total_rtvs[k] = v

    return total_rtvs
