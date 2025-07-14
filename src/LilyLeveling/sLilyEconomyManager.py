import discord
from discord.ext import commands
import json


data = {}

def LoadData():
    global data
    with open("src/LilyLeveling/EconomyConfig.json", "r") as Data:
        data = json.load(Data)

LoadData()

async def DisplayShop():
    pass