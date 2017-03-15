
class QuantityException(Exception):

    def __init__(self,q1,q2,Type=1):
        if Type==1:
            self.describe=\
                "The absolute value (%s) of the quantity to be closed should be lower than that of the holding position (%s)"\
                % (q1,q2)
        elif Type==2:
            self.describe = \
               'quantity_1 * quantity_2 = %d * %d = %d < 0\n the product of the 2 quantities is supposed to be > 0'\
                      % (q1,q2,q1*q2)

    def __str__(self):
        return  self.describe
