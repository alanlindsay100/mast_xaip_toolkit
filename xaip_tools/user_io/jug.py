from mlconjug3 import Conjugator as jug
import inspect


c= jug(language="en")

def conjugate(v):
  v = c.conjugate(v)
  return list(set(map(lambda x: x[-1], v.iterate())))


if __name__ == '__main__':
  print (conjugate("go"))
  print (conjugate("move"))
  print (conjugate("survey"))
  print (conjugate("target"))
  
