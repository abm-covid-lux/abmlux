
# TODO: document!
def multinoulli(problist):
    p = random.randint(1,np.sum(problist))
    summ = 0
    for i in range(problist.size):
        summ = summ + problist[i]
        if summ >= p:
            return i

