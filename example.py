from ratelimitqueue import RateLimitQueue
from multiprocessing import Pool
import time
import random


def call_slow_api(id):
    time.sleep(random.uniform(1,2))
    return f'This is the data for item {id}'


if __name__ == '__main__':

    rlq = RateLimitQueue(calls=3, per=2)

    with Pool(4, do_work, (rlq, start)) as p:
        p.

    t = Thread(target=do_work, args=(rlq, start, 10))
    t.start()

    for i in range(10):
        rlq.put(i)
        print(f'Put item {i} after {time.time()-start:.2f} seconds.')

    # t.join()


