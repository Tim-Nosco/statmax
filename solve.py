import re
import subprocess
import logging

logger = logging.getLogger('solve.py')
logging.basicConfig()
logger.setLevel(logging.DEBUG)

def hook():
	#for debugging
	import IPython
	IPython.embed()
	exit(0)

class Profile:
	stats = ["crit", "mastery", "haste", "versatility"]
	def __init__(self, raw, is_base=False, values=None):
		logger.debug("New profile object")
		self.is_base=is_base
		self.raw = raw
		if values:
			self.values=values
			# self.values = dict()
			# for key in values:
			# 	self.values[key] = int(values[key])
		else:
			base=r"gear_{}_rating=(\d+)\s"
			matches = (re.search(base.format(x),raw) for x in self.stats)
			self.as_list = [int(m.group(1)) if m else 0 for m in matches]
			self.values = dict(zip(self.stats,self.as_list))
		self.total = sum(self.values.values())
		logger.debug("Found the following stats: %s",self.values)

	def adjust_stats(self,target):
		assert(self.is_base)
		logger.debug("Making a new profile.")
		stat_str = ""
		for key in target:
			# diff = int(target[key])-self.values[key]
			diff = target[key]-self.values[key]
			if diff:
				fmt = "_{}{}" if stat_str else "{}{}"
				stat_str+=fmt.format(diff,key)
		new_profile = self.raw
		if stat_str:
			#add a shirt
			m = re.search("shirt=(\S+)",self.raw)
			base = m.group(1) if m else "artisan_officers_shirt,id=89195"
			new_shirt="\nshirt={},stats={}".format(base, stat_str)
			logger.info("Putting on a new shirt %s",new_shirt)
			new_profile+=new_shirt
		goal = self.values.copy()
		goal.update(target)
		return Profile(new_profile,values=goal)

	def sim(self):
		simc_input = "/tmp/statmax.simc"
		with open(simc_input, 'w') as f:
			f.write(self.raw)
		argv = ["/home/jocular/Downloads/simc/engine/simc",
				simc_input]
		logger.info("Starting %s", argv)
		out = subprocess.check_output(argv)
		logger.debug("Simc finished.")
		# logger.debug("Simc output: \n%s", out)
		r = r"DPS Ranking:\s(\d+)\s.+Raid"
		m = re.search(r,out)
		dps = int(m.group(1)) if m else None
		logger.info("Sim ended with %s DPS.", dps)
		return dps

	def optimizer(self,args):
		return -1*self.adjust_stats(dict(zip(self.stats,args))).sim()

	def constraint(self,args):
		return self.total-sum(args)

def read_profile_from_file(filename):
	with open(filename, "r") as f:
		data = f.read()
	logger.debug("Read %s bytes from %s.",len(data),filename)
	return Profile(data,True)

start_profile = read_profile_from_file("mage_test")
orig = start_profile.sim()

from scipy.optimize import minimize

res = minimize( start_profile.optimizer, 
				start_profile.as_list,
				method="COBYLA",
				constraints={'type': 'ineq', 
							 'fun': start_profile.constraint},
				bounds=[(0,None),(0,None),(0,None)],
				options={'rhobeg':1000})

print "Stat order: {}".format(start_profile.stats)
print "FOUND: {}".format(res)
print "ORIG: {} with stats: {}".format(orig, start_profile.as_list)
