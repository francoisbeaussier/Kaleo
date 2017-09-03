#!/usr/bin/python

from __future__ import division

import sys, getopt
from struct import unpack

locale = "US" #change this for different language

initialoffset = 80
initialoffsetability = 100
#stagedatalength = 92
#pokemondatalength = 36
pokemonattacklength = 7
pokemonabilitylength = 36
maxlevel = 30

#pokemonlist = []

type_overrides = [0,1,3,4,2,6,5,7,8,9,10,12,11,14,13,15,16,17]
#this list patches the fact that the type names in messagePokemonType_whatever are out of order compared to what the records expect. If the typeindex is, say, 6 [for Rock], this list will redirect it to type list entry 5 (where 'Rock' is actually stored, instead of the wrong value, 'Bug').
#If GS ever switches this up, or it turns out to be different in different locales, this list can be reset to compensate.
#remember, if the pokemon record says the type is index#X, then the actual location of that should be in type_overrides[X].

#pokemontypelist = []
pokemonabilitylist = []
dropitems = {"1":"RML", "3":"EBS", "4":"EBM", "5":"EBL", "6":"SBS", "7":"SBM", "8":"SBL", "10":"MSU", "23":"10 Hearts", "30":"5000 Coins", "32":"PSB"}


class BinStorage:
	def __init__(self, binFile):
		try:
			with open(binFile, "rb") as file:
				self.contents = file.read()
		except IOError:
			sys.stderr.write("Couldn't open the file {}. Please check the file is present.\n".format(binFile))
			sys.exit(1)
			
		self.num_records = unpack("<I",self.contents[0:4])[0]
		self.record_len = unpack("<I",self.contents[4:8])[0]
		self.text_start_point = unpack("<I",self.contents[8:12])[0]
		#I'm only 50% sure this is the text segment start point. Further investigation required.
		self.data_start_point = unpack("<I",self.contents[16:20])[0]
		self.third_seg_start_point = unpack("<I",self.contents[24:28])[0]
		#this is the start of the segment that comes after the data segment of .bin files. Is it some kind of index? I have no clue.
		
		self.text_only_len = unpack("<I",self.contents[52:56])[0]
		#length of text segment sans file internal ID. Used for message bins.
		
	def getAll(self):
		return self.contents
		
	def getRecord(self,index):
		record_start = self.data_start_point + index * self.record_len
		return self.contents[record_start:record_start+self.record_len]	

	def getHeader(self):
		return self.contents[:self.text_start_point]
		
	def getTextSegment(self):
		return self.contents[self.text_start_point:self.data_start_point]
		
	def getMessage(self, index,fullWidth=False):
		#this gets a message from a message .bin. Important: IT ONLY WORKS ON MESSAGE BINS - their data segment is an index for their text segment. If you try it on any other .bin, expect gibberish.
		if index >= self.num_records:
			raise IndexError
		
		messageStart = unpack("<I", self.getRecord(index))[0]
		if index == self.num_records - 1:
			#last message:
			message = self.contents[messageStart:self.text_start_point+self.text_only_len-5]
			#the 5 is for the string 'data ' that sits after text but before name and data
		else:
			nextMessageStart = unpack("<I", self.getRecord(index+1))[0]
			message = self.contents[messageStart:nextMessageStart]
	
		final_message = ""
		if not fullWidth:
			final_message = "".join([message[char] for char in range(0,len(message),2) if message[char] != "\x00"])
		else:
			final_message = "".join([message[char:char+2] for char in range(0,len(message),2) if message[char:char+2] != "\x00\x00"])
		
		return final_message
			
	def getAllRecords(self):
		return self.contents[self.data_start_point:self.third_start_point]
		
	def getThirdSegment(self):
		return self.contents[self.third_start_point:]

class PokemonDataRecord:
	def __init__(self,index,snippet,namingBin,typeBin):
			#this is for finding the names
			
		self.binary = snippet
		self.index = index	
			
		#this is for finding the types
		#if len(pokemontypelist) == 0:
		#	definepokemontypelist()
	
		#this is for finding the types
		if len(pokemonabilitylist) == 0:
			definepokemonabilitylist()

		#parse!
		self.dex = readbits(snippet, 0, 0, 10)
		self.typeindex = readbits(snippet, 1, 3, 5)
		self.abilityindex = readbits(snippet, 2, 0, 8)
		self.bpindex = readbits(snippet, 3, 0, 4) #index of base power of the pokemon
		self.rmls = readbits(snippet, 4, 0, 6)
		self.nameindex = readbits(snippet, 6, 5, 11)
		self.modifierindex = readbits(snippet, 8, 0, 8)
		self.classtype = readbits(snippet, 9, 4, 3) #0 means it's a Pokemon, 2 means it's a Mega Pokemon
		self.icons = readbits(snippet, 10, 0, 7)
		self.msu = readbits(snippet, 10, 7, 7)
		self.megastoneindex = readbits(snippet, 12, 0, 11) #refers to the Index number of the mega stone
		self.megaindex = readbits(snippet, 13, 3, 11) #refers to the Index number of the base mega pokemon
		self.ss1index = readbyte(snippet, 32)
		self.ss2index = readbyte(snippet, 33)
		self.ss3index = readbyte(snippet, 34)
		self.ss4index = readbyte(snippet, 35)
	
		#determine a few values
		#name and modifier
		try:
			self.name = namingBin.getMessage(self.nameindex)
			#print self.name
		except IndexError:
			self.name = "UNKNOWN ({})".format(self.nameindex)
		if self.modifierindex != 0:
			self.modifierindex += 768
			try:
				self.modifier = namingBin.getMessage(self.modifierindex)
			except IndexError:
				self.modifier = "UNKNOWN ({})".format(self.modifierindex)
		else:
			self.modifier = ""
	
		#type
		try:
			#self.type = pokemontypelist[self.typeindex]
			self.type = typeBin.getMessage(type_overrides[self.typeindex])
		except IndexError:
			self.type = "UNKNOWN ({})".format(self.typeindex)
	
		#ap list
		self.aplist = PokemonAttack(self.bpindex).APs #this function does a nice job
	
		#ability and skill swapper abilities
		try:
			self.ability = pokemonabilitylist[self.abilityindex]
		except IndexError:
			self.ability = "UNKNOWN ({})".format(self.ability)
		try:
			if (self.ss1index != 0):
				self.ss1 = pokemonabilitylist[self.ss1index]
		except IndexError:
			self.ss1 = "UNKNOWN ({})".format(self.ss1index)
		try:
			if (self.ss2index !=0):
				self.ss2 = pokemonabilitylist[self.ss2index]
		except IndexError:
			self.ss2 = "UNKNOWN ({})".format(self.ss2index)
		try:
			if (self.ss3index != 0):
				self.ss3 = pokemonabilitylist[self.ss3index]
		except IndexError:
			self.ss3 = "UNKNOWN ({})".format(self.ss3index)
		try:
			if (self.ss4index != 0):
				self.ss4 = pokemonabilitylist[self.ss4index]
		except IndexError:
			self.ss4 = "UNKNOWN ({})".format(self.ss4index)
	
		#mega stone
		try:
			if (self.megastoneindex != 0):
				self.megastone = PokemonData.getPokemonInfo(self.megastoneindex)
		except IndexError:
			self.megastone = ""

#PokemonDataRecord class ends.

class PokemonData:
	
	#now using singleton design pattern - that is, there is only ever one PokemonData instance. 
	
	databin = None
	namebin = None
	typebin = None
	records = []
	
	#this constructor is now PRIVATE. Please do not use it; please use getPokemonInfo.
	def __init__(self):
		#open file and store data - extraction is handled by getData and the PokemonDataRecord nested class
		if self.databin is not None:
			sys.stderr.write("Something is wrong. The init for PokemonData was called more than once.")
			sys.exit(1)
		self.databin = BinStorage("pokemonData.bin")
		self.namebin = BinStorage("messagePokemonList_"+locale+".bin")
		self.typebin = BinStorage("messagePokemonType_"+locale+".bin")
		self.records = [None for item in range(self.databin.num_records)]
	
	@classmethod
	def getPokemonInfo(thisClass, index):
		if thisClass.databin is None:
			thisClass = thisClass()
		if thisClass.records[index] is None:
			thisClass.records[index] = PokemonDataRecord(index, thisClass.databin.getRecord(index),thisClass.namebin,thisClass.typebin)
		return thisClass.records[index]
	
	@classmethod
	def printdata(thisClass,index):
		record = thisClass.getPokemonInfo(index)
	
		if (record.classtype == 0): 
			print "Pokemon Index " + str(record.index)
			
			pokemonfullname = record.name
			if (record.modifier != ""):
				pokemonfullname += " (" + record.modifier + ")"
			print "Name: " + pokemonfullname
			print "Dex: " + str(record.dex)
			print "Type: " + str(record.type)
			print "BP: " + str(record.aplist[0])
			print "RMLs: " + str(record.rmls)
			print "Ability: " + str(record.ability) + " (index " + str(record.abilityindex) + ")"
			if (record.ss1index !=0):	 #only display the skill swapper ability if it has one
				print "SS Ability 1: " + str(record.ss1) + " (index " + str(record.ss1index) + ")"
			if (record.ss2index != 0):
				print "SS Ability 2: " + str(record.ss2) + " (index " + str(record.ss2index) + ")"
			if (record.ss3index != 0):
				print "SS Ability 3: " + str(record.ss3) + " (index " + str(record.ss3index) + ")"
			if (record.ss4index != 0):
				print "SS Ability 4: " + str(record.ss4) + " (index " + str(record.ss4index) + ")"
			
		elif (record.classtype == 2):
			print "Pokemon Index " + str(record.index)
			pokemonfullname = record.name
			if (record.modifier != ""):
				pokemonfullname += " (" + record.modifier + ")"
			print "Name: " + pokemonfullname
			print "Mega Stone: " + str(record.megastone.name) + " (Index " + str(record.megastoneindex) + ")"
			print "Dex: " + str(record.dex)
			print "Type: " + str(record.type)
			print "Icons to Mega Evolve: " + str(record.icons)
			print "MSUs Available: " + str(record.msu)
			
		else:
			print "Index " + str(record.index)
			pokemonfullname = record.name
			if (record.modifier != ""):
				pokemonfullname += " (" + record.modifier + ")"
			print "Name: " + pokemonfullname
	
	
	@classmethod
	def printalldata(thisClass):
		if thisClass.databin is None:
			thisClass = thisClass()
		for record in range(thisClass.databin.num_records):
			thisClass.printdata(record)
			print #blank line between records!
	
	@classmethod			
	def printbinary(thisClass,index):
		if thisClass.databin is None:
			thisClass = thisClass()
		record = thisClass.databin.getRecord(index)
		print "\n".join(format(ord(x), 'b') for x in record.binary)


class StageDataRecord:
	def __init__(self,index,snippet):
		self.binary = snippet
		self.index = index
		
		#parse!
		self.pokemonindex = readbits(snippet, 0, 0, 10)
		self.megapokemon = readbits(snippet, 1, 2, 4) #determines if the pokemon is a mega pokemon
		self.numsupports = readbits(snippet, 1, 6, 4)
		self.timed = readbits(snippet, 2, 2, 1)
		self.seconds = readbits(snippet, 2, 3, 8)
		self.hp = readbits(snippet, 4, 0, 20)
		self.attemptcost = readbits(snippet, 8, 0, 16) #can't tell if hearts or coins yet
		self.srank = readbits(snippet, 48, 2, 10)
		self.arank = readbits(snippet, 49, 4, 10)
		self.brank = readbits(snippet, 50, 6, 10)
		self.basecatch = readbits(snippet, 52, 0, 7)
		self.bonuscatch = readbits(snippet, 52, 7, 7)
		self.coinrewardrepeat = readbits(snippet, 56, 7, 16)
		self.coinrewardfirst = readbits(snippet, 60, 0, 16)
		self.exp = readbits(snippet, 64, 0, 16)
		self.drop1item = readbits(snippet, 67, 0, 8)
		self.drop1rate = readbits(snippet, 68, 0, 4)
		self.drop2item = readbits(snippet, 68, 4, 8)
		self.drop2rate = readbits(snippet, 69, 4, 4)
		self.drop3item = readbits(snippet, 70, 0, 8)
		self.drop3rate = readbits(snippet, 71, 0, 4)
		self.trackid = readbits(snippet, 72, 3, 6)
		self.extrahp = readbits(snippet, 80, 0, 16)
		self.moves = readbits(snippet, 86, 0, 8)
		self.backgroundid = readbits(snippet, 88, 2, 8)

		#unknown values for now
		self.defaultsetindex = readbits(snippet, 84, 0, 16)
		#default supports - i.e. what's in the skyfall 
		
		self.layoutindex = readbits(snippet, 82, 0, 16)
		#layout = stage layout data. starting board.
		
		#determine a few values
		if self.megapokemon == 1:
			self.pokemonindex += 1024
		self.pokemon = PokemonData.getPokemonInfo(self.pokemonindex)


class StageData:
	databin = None
	records = []
	
	def __init__(self,stage_file):
		self.databin = BinStorage(stage_file)
		self.records = [None for item in range(self.databin.num_records)]
	
	def getStageInfo(self, index):
		if self.records[index] is None:
			self.records[index] = StageDataRecord(index, self.databin.getRecord(index))
		return self.records[index]
	
	def printdata(self,index):
		record = self.getStageInfo(index)
	
		print "Stage Index " + str(record.index)
		
		pokemonfullname = record.pokemon.name
		if (record.pokemon.modifier != ""):
			pokemonfullname += " (" + record.pokemon.modifier + ")"
		print "Pokemon: " + pokemonfullname
		
		hpstring = "HP: " + str(record.hp)
		if (record.extrahp != 0):
			hpstring += " + " + str(record.extrahp)
		print hpstring
		if (record.timed == 0):
			print "Moves: " + str(record.moves)
		else:
			print "Seconds: " + str(record.seconds)
		print "Experience: " + str(record.exp)
		
		if (record.timed == 0):
			print "Catchability: " + str(record.basecatch) + "% + " + str(record.bonuscatch) + "%/move"
		else:
			print "Catchability: " + str(record.basecatch) + "% + " + str(record.bonuscatch) + "%/3sec"
		
		print "# of Support Pokemon: " + str(record.numsupports)
		print "Rank Requirements: " + str(record.srank) + " / " + str(record.arank) + " / " + str(record.brank)
		
		print "Coin reward (first clear): " + str(record.coinrewardfirst)
		print "Coin reward (repeat clear): " + str(record.coinrewardrepeat)
		print "Background ID: " + str(record.backgroundid)
		print "Track ID: " + str(record.trackid)
		print "Cost to play the stage: " + str(record.attemptcost)
		
		if (record.drop1item != 0 or record.drop2item != 0 or record.drop3item != 0):
			try:
				drop1item = dropitems[str(record.drop1item)]
			except KeyError:
				drop1item = record.drop1item
			try:
				drop2item = dropitems[str(record.drop2item)]
			except KeyError:
				drop2item = record.drop2item
			try:
				drop3item = dropitems[str(record.drop3item)]
			except KeyError:
				drop3item = record.drop3item
			print "Drop Items: " + str(drop1item) + " / " + str(drop2item) + " / " + str(drop3item)
			print "Drop Rates: " + str(1/pow(2,record.drop1rate-1)) + " / " + str(1/pow(2,record.drop2rate-1)) + " / " + str(1/pow(2,record.drop3rate-1))
		
		#BITS UNACCOUNTED FOR:
		
		#...this list may be old.
		
	    #from byte 6, bit 5 to byte 48, bit 2 (almost certainly disruptions) [41 bytes, 6 bits (334)]
	    #from byte 53, bit 7 to byte 56, bit 7 [3 bytes, 1 bit (25)]
	    #byte 56, bit 8 and all of byte 57 [9 bits]
	    #bytes 62 and 63
	    #byte 66
	    #4 bits of byte 71 and 3 bits of byte 72 [(7)]
	    #5 bits of byte 74, bytes 75-79 [(45)]
	    #byte 87 and 2 bits of byte 88
	    #6 bits of byte 89, and then bytes 90-91
	
	    #STAGE QUALITIES UNDISCOVERED:
	    #Disruptions. 
	    #Entry fee. lock entry fee.
	    # # plays allowed (before disappearing).
	    # same (before 'locking' and after and all that nonsense).
	    #start/end dates? or is this found elsewhere?
	    
	def printalldata(self):
		for record in range(self.databin.num_records):
			self.printdata(record)
			print #blank line between records!
	
	def printbinary(self,index):
		record = self.databin.getRecord(index)
		print "\n".join(format(ord(x), 'b') for x in record.binary)

class PokemonAttack:
	def __init__(self, index):
		self.index = index-1
		
		#open file and... grab the whole thing
		file = open("pokemonAttack.bin", "rb")
		contents = file.read()
		begin = initialoffset
		end = begin + (pokemonattacklength * maxlevel)
		snippet = contents[begin:end]
		self.binary = snippet
		file.close()
		
		#Parse the AP values of all levels, given the BP index
		self.APs = []
		for i in range(maxlevel):
			self.APs.append(readbyte(snippet, (pokemonattacklength*i) + self.index))

class PokemonAbility:
	def __init__(self, index):
		self.index = index
		
		#open file and extract the snippet we need
		file = open("pokemonAbility.bin", "rb")
		contents = file.read()
		begin = initialoffsetability + (pokemonabilitylength * index)
		end = begin + pokemonabilitylength
		snippet = contents[begin:end]
		self.binary = snippet
		
		#snippet of the ability BEFORE this one, why? because apparently certain data for THIS ability is stored there. ??????
		begin2 = initialoffsetability + (pokemonabilitylength * (index-1))
		end2 = begin + pokemonabilitylength
		snippet2 = contents[begin2:end2]
		self.binary2 = snippet2
	
		file.close()
	
		#this is for finding the names and descriptions
		if len(pokemonabilitylist) == 0:
			definepokemonabilitylist()
		
		#parse!
		self.type = readbyte(snippet, 4)
		self.rate3 = readbyte(snippet, 5)
		self.rate4 = readbyte(snippet, 6)
		self.rate5 = readbyte(snippet, 7)
		self.nameindex = readbyte(snippet, 8) #index in the search dropdown menu
		self.bonuseffect = readbyte(snippet, 9) #1 if bonus affects activation rate, 2 if bonus affects damage
		self.sp1 = readbyte(snippet, 10)
		self.sp2 = readbyte(snippet, 11)
		self.sp3 = readbyte(snippet, 12)
		self.sp4 = readbyte(snippet, 13)
		self.damagemultiplier = round(unpack("f", self.binary2[16:20])[0], 2)
		self.bonus1 = round(unpack("f", self.binary2[20:24])[0], 2)
		self.bonus2 = round(unpack("f", self.binary2[24:28])[0], 2)
		self.bonus3 = round(unpack("f", self.binary2[28:32])[0], 2)
		self.bonus4 = round(unpack("f", self.binary2[32:36])[0], 2)
		
		#determine a few values
		self.name = pokemonabilitylist[self.index]
		#self.desc = pokemonabilitylist[self.descindex + 159]
	
	def printdata(self):
		print "Ability Index " + str(self.index)
		print "Name: " + str(self.name)
		#print "Description: " + str(self.desc)
		print "type: " + str(self.type)
		print "Activation Rates: " + str(self.rate3) + "% / " + str(self.rate4) + "% / " + str(self.rate5) + "%"
		print "Damage Multiplier: " + str(self.damagemultiplier)
		
		bonus1string = "Bonus 1: " + str(self.bonus1)
		bonus2string = "Bonus 2: " + str(self.bonus2)
		bonus3string = "Bonus 3: " + str(self.bonus3)
		bonus4string = "Bonus 4: " + str(self.bonus4)
		if (self.bonuseffect == 1):
		    if (self.rate3 != 0):
		        self.sl2rate3 = min(int(self.rate3 + self.bonus1), 100)
		        self.sl3rate3 = min(int(self.rate3 + self.bonus2), 100)
		        self.sl4rate3 = min(int(self.rate3 + self.bonus3), 100)
		        self.sl5rate3 = min(int(self.rate3 + self.bonus4), 100)
		    else:
		        self.sl2rate3, self.sl3rate3, self.sl4rate3, self.sl5rate3 = (0,0,0,0)
		    if (self.rate4 != 0):
		        self.sl2rate4 = min(int(self.rate4 + self.bonus1), 100)
		        self.sl3rate4 = min(int(self.rate4 + self.bonus2), 100)
		        self.sl4rate4 = min(int(self.rate4 + self.bonus3), 100)
		        self.sl5rate4 = min(int(self.rate4 + self.bonus4), 100)
		    else:
		        self.sl2rate4, self.sl3rate4, self.sl4rate4, self.sl5rate4 = (0,0,0,0)
		    if (self.rate5 != 0):
		        self.sl2rate5 = min(int(self.rate5 + self.bonus1), 100)
		        self.sl3rate5 = min(int(self.rate5 + self.bonus2), 100)
		        self.sl4rate5 = min(int(self.rate5 + self.bonus3), 100)
		        self.sl5rate5 = min(int(self.rate5 + self.bonus4), 100)
		    else:
		        self.sl2rate5, self.sl3rate5, self.sl4rate5, self.sl5rate5 = (0,0,0,0)
		    bonus1string += " (" + str(self.sl2rate3) + "% / " + str(self.sl2rate4) + "% / " + str(self.sl2rate5) + "%)"
		    bonus2string += " (" + str(self.sl3rate3) + "% / " + str(self.sl3rate4) + "% / " + str(self.sl3rate5) + "%)"
		    bonus3string += " (" + str(self.sl4rate3) + "% / " + str(self.sl4rate4) + "% / " + str(self.sl4rate5) + "%)"
		    bonus4string += " (" + str(self.sl5rate3) + "% / " + str(self.sl5rate4) + "% / " + str(self.sl5rate5) + "%)"
		elif (self.bonuseffect == 2):
		    bonus1string += " (" + str(self.damagemultiplier * self.bonus1) + ")"
		    bonus2string += " (" + str(self.damagemultiplier * self.bonus2) + ")"
		    bonus3string += " (" + str(self.damagemultiplier * self.bonus3) + ")"
		    bonus4string += " (" + str(self.damagemultiplier * self.bonus4) + ")"
		print bonus1string
		print bonus2string
		print bonus3string
		print bonus4string
		
		print "SP Requirements: " + str(self.sp1) + " -> " + str(self.sp2) + " -> " + str(self.sp3) + " -> " + str(self.sp4)
		
		print "nameindex: " + str(self.nameindex)
		print "unknownbyte0: " + str(readbyte(self.binary, 0))
		print "unknownbyte1: " + str(readbyte(self.binary, 1))
		print "unknownbyte2: " + str(readbyte(self.binary, 2))
		print "unknownbyte3: " + str(readbyte(self.binary, 3))
		print "unknownbyte14: " + str(readbyte(self.binary, 14))
		print "unknownbyte15: " + str(readbyte(self.binary, 15))
	
	def printbinary(self):
		print "\n".join(format(ord(x), 'b') for x in self.binary)

def main(args):
	#make sure correct number of arguments
	if len(args) != 2:
		print 'need 2 arguments: datatype, index'
		sys.exit()
	
	#parse arguments
	datatype = args[0]
	index = args[1]
	
	try:
		if datatype == "stage":
			sdata = StageData("stageData.bin")
			if index == "all":
				sdata.printalldata()
			else:
				sdata.printdata(int(index))
		
		elif datatype == "expertstage":
			sdata = StageData("stageDataExtra.bin")
			if index == "all":
				sdata.printalldata()
			else:
				sdata.printdata(int(index))
		
		elif datatype == "eventstage":
			sdata = StageData("stageDataEvent.bin")
			if index == "all":
				sdata.printalldata()
			else:
				sdata.printdata(int(index))
		
		elif datatype == "pokemon":
			if index == "all":
				PokemonData.printalldata()
			else:
				PokemonData.printdata(int(index))
		
		elif datatype == "ability":
			if index == "all":
				numentries = getnumentries("pokemonAbility.bin")
				for i in range(numentries):
					adata = PokemonAbility(i)
					adata.printdata()
					print
			else:
				adata = PokemonAbility(int(index))
				adata.printdata()
		
		else:
			sys.stderr.write("datatype should be stage, expertstage, eventstage, pokemon, or ability\n")
	except IOError:
		sys.stderr.write("Couldn't find the bin file to extract data from.\n")
		raise

#Reads a certain number of bits starting from an offset byte and bit and returns the value
def readbits(text, offsetbyte, offsetbit, numbits):
	ans = ""
	bytes = [ord(b) for b in text[offsetbyte:offsetbyte+4]]
	val = 0
	for i in reversed(xrange(4)):
		val *= 256
		val += bytes[i]
	val >>= offsetbit
	val &= (1 << numbits) -1
	return val

def readbyte(text, offsetbyte):
	return ord(text[offsetbyte])

#Checks the first 2 bytes of a file and returns the value
def getnumentries(filename):
	file = open(filename, "rb")
	contents = file.read()
	numentries = readbits(contents, 0, 0, 32)
	file.close()
	return numentries

#Defines the global list for pokemon types
# def definepokemontypelist():
# 	try:
# 		listfile = open("pokemontypelist.txt", "r")
# 		thewholething2 = listfile.read()
# 		global pokemontypelist
# 		pokemontypelist = thewholething2.split("\n")
# 		listfile.close()
# 	except IOError:
# 		sys.stderr.write("Couldn't find pokemontypelist.txt to retrieve Pokemon types.\n")
# 		pokemontypelist = [""] #to prevent calling this function again

#Defines the global list for pokemon abilities and descriptions
def definepokemonabilitylist():
	try:
		listfile = open("pokemonabilitylist.txt", "r")
		thewholething2 = listfile.read()
		global pokemonabilitylist
		pokemonabilitylist = thewholething2.split("\n")
		listfile.close()
	except IOError:
		sys.stderr.write("Couldn't find pokemonabilitylist.txt to retrieve Pokemon abilities.\n")
		pokemonabilitylist = [""] #to prevent calling this function again


if __name__ == "__main__":
	main(sys.argv[1:])
