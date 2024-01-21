# This code is based on the following example:
# https://discordpy.readthedocs.io/en/stable/quickstart.html#a-minimal-bot

import os
import time
import random
import threading
import asyncio
import math
from collections import Counter

import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
from discord import Embed

from keep_alive import keep_alive
import requests


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
user_data = {}
user_stock = {}
count = 1
price = 10
stop_loop = False


def is_same_user(message):
  return message.author == user


def update_stock():
  global price
  while True:
    random_int = random.randint(100, 1300)
    if random_int == 103:
      print("jackpot")
      if price < 3:
        price = price + 60
      price = price**2
    if random_int == 1227:
      print("fuck")
      price = price / 3
    change = round(random.uniform(-0.3 * price, 0.3 * price), 2)
    if change < 0 and price + change <= 0.13:
      change = abs(change)
    if (price + change) >= 49 and (price + change) <= 51:
      change = -40
    price += change
    price = round(price, 2)  # Ensure the price doesn't drop below 0.1
    print(price)
    time.sleep(3)


def get_score(arr):
  score = 0
  for i in arr:
    score = score + i
  return score


def is_positive_integer(content):
  if content == "all":
    return True
  try:
    number = int(content)
    return number >= 0
  except ValueError:
    return False


@client.event
async def on_ready():
  print('We have logged in as {0.user}'.format(client))


background_thread = threading.Thread(target=update_stock)
background_thread.daemon = True  # The thread will exit when the main program exits


@client.event
async def on_message(message):
  global stop_loop
  user = message.author
  if message.author == client.user:
    return
  if message.content.startswith('stop'):
    stop_loop = False
  if message.content.startswith('reset'):
    user_data[user] = 100
    await message.channel.send('Your score has been reset')
  if message.content.startswith('show me'):
    user_data[user] = 1000
    await message.channel.send('Showed your money')

  if message.content.startswith('$$'):
    global count, tie
    if not background_thread.is_alive():
      background_thread.start()
    count = 1
    tie = False
    await message.channel.send(
        'Hello! Welcome to the casino!\n Please press a button for the game you like to play!'
    )
    black = Button(label="Black Jack",
                   style=discord.ButtonStyle.blurple,
                   disabled=False,
                   emoji="🃏")
    money = Button(label="Account",
                   style=discord.ButtonStyle.green,
                   emoji="🏅",
                   disabled=False)
    stock = Button(label="Stocks",
                   style=discord.ButtonStyle.blurple,
                   disabled=False,
                   emoji="📈")
    slot = Button(label="Slot Machine",
                  style=discord.ButtonStyle.blurple,
                  emoji="🎰")
    view = View(timeout=None)
    view.add_item(black)
    view.add_item(slot)
    view.add_item(stock)
    view.add_item(money)

    await message.channel.send(view=view)

    ######Money Button######
    async def on_money_click(interaction):
      global user
      user = message.author
      if user not in user_data:
        user_data[user] = 100  # Set a default value for the user

      token = round(user_data[user], 2)
      await interaction.response.send_message(
          f"Currently {user.display_name} you have {token} tokens")
      money.disabled = True
      await interaction.message.edit(view=view)

    money.callback = on_money_click

    ####stock Button####
    async def on_stock_click(interaction):
      global user
      user = message.author
      if user not in user_data:
        user_data[user] = 100  # Set a default value for the user

      money.disabled = True
      black.disabled = True
      slot.disabled = True
      stock.disabled = True
      await interaction.message.edit(view=view)
      await interaction.response.send_message(
          f"{user.display_name} clicked Stock! \n")

      price = Button(label="Market price",
                     style=discord.ButtonStyle.blurple,
                     emoji="💵",
                     disabled=False)
      buy = Button(label="Buy", style=discord.ButtonStyle.green)
      sell = Button(label="Sell", style=discord.ButtonStyle.red)
      wallet = Button(label="Wallet",
                      style=discord.ButtonStyle.blurple,
                      emoji="🏦")

      stock_view = View(timeout=None)
      stock_view.add_item(price)
      stock_view.add_item(buy)
      stock_view.add_item(sell)
      stock_view.add_item(wallet)
      await interaction.message.edit(view=stock_view)

      if not background_thread.is_alive():
        background_thread.start()

      async def on_price_click(interaction):
        global price, stop_loop
        stop_loop = True
        await interaction.response.send_message("Market Price")
        current = price
        embed = discord.Embed(title="Current market price is: {current}",
                              description="")
        message = await interaction.followup.send(embed=embed)

        while True:
          if current != price:
            current = price
            embed.title = f"Current market price is: {current}"
            await message.edit(embed=embed)
          if not stop_loop:
            break

      async def on_buy_click(interaction):
        global user, user_data, user_stock, price, stop_loop
        user = interaction.user
        if user_data[user] < 1:
          await interaction.response.send_message(
              f"{user.display_name} don't have enough coins to play this game. You need at least 100 tokens."
          )
        else:
          await interaction.response.send_message(
              "How many stocks do you want to buy?")
          message = await client.wait_for("message",
                                          check=lambda msg: is_same_user(msg)
                                          and is_positive_integer(msg.content))
          input = message.content
          if input.startswith("all"):
            stock_amount = math.floor(user_data[user] / price)
          else:
            stock_amount = int(input)
          if stock_amount == 0:
            await message.channel.send(f"You didn't buy any stocks")
            return
          current = price
          stop_loop = False
          if stock_amount * current > user_data[user]:
            await message.channel.send(f"You can't buy that many stocks")
          else:
            user_data[user] -= stock_amount * current
            if user not in user_stock:
              user_stock[user] = [stock_amount, current]
            else:
              amount = user_stock[user][0]
              before = user_stock[user][1]
              user_stock[user][0] += stock_amount
              user_stock[user][1] = (
                  (amount * before) +
                  (stock_amount * current)) / user_stock[user][0]

            await message.channel.send(
                f"{user.display_name} bought {stock_amount} stocks at price: {current}"
            )

      async def on_sell_click(interaction):
        global user, user_data, user_stock, price, stop_loop
        user = interaction.user
        await interaction.response.send_message(
            "How many stocks do you want to sell?")
        message = await client.wait_for("message",
                                        check=lambda msg: is_same_user(msg) and
                                        is_positive_integer(msg.content))
        input = message.content
        if input.startswith("all"):
          stock_amount = user_stock[user][0]
        else:
          stock_amount = int(message.content)
        if stock_amount == 0:
          await message.channel.send(f"You didn't sell any stocks")

          return
        stop_loop = False
        if stock_amount > user_stock[user][0]:
          await message.channel.send(f"You can't sell that many stocks")
        else:
          current = price
          user_data[user] += round(stock_amount * current, 0)
          user_stock[user][0] -= stock_amount
          profit = round(
              stock_amount * current - user_stock[user][1] * stock_amount, 2)
          await message.channel.send(
              f"{user.display_name} sold {stock_amount} stocks at price: {current} \nyou earned {profit} tokens"
          )

      async def on_wallet_click(interaction):
        global user
        global user_data
        global user_stock
        global price
        user = interaction.user
        if user not in user_stock:
          await interaction.response.send_message("You don't have any stocks")
        elif user_stock[user][0] == 0:
          await interaction.response.send_message("You don't have any stocks")
        else:
          count = round(user_stock[user][1], 2)
          await interaction.response.send_message(
              f"{user.display_name} has {user_stock[user][0]} many stocks \nand has average price of {count}"
          )

      price.callback = on_price_click
      buy.callback = on_buy_click
      sell.callback = on_sell_click
      wallet.callback = on_wallet_click


    ######Black jack Button######
    async def on_black_click(interaction, mult):

      money.disabled = True
      slot.disabled = True
      await interaction.message.edit(view=view)

      user = interaction.user
      if user not in user_data:
        user_data[user] = 100

      if user_data[user] < 100:
        await interaction.response.send_message(
            f"{user.display_name} don't have enough coins to play this game. You need at least 100 tokens."
        )
        black.disabled = True
        await interaction.message.edit(view=view)

      else:
        await interaction.response.send_message(
            f"{user.display_name} clicked Black Jack! \n")
        black.disabled = True
        await interaction.message.edit(view=view)
        time.sleep(0.5)
        await message.channel.send("shuffling cards...\n")
        time.sleep(1)

        hit = Button(label='HIT',
                     style=discord.ButtonStyle.green,
                     disabled=False)
        stand = Button(label='STAND',
                       style=discord.ButtonStyle.red,
                       disabled=False)
        replay = Button(label="play again?",
                        style=discord.ButtonStyle.blurple,
                        disabled=False)
        deal = Button(label="dealing..", disabled=True)
        double = Button(label='Double or Nothing?',
                        style=discord.ButtonStyle.red)
        quit = Button(label='Quit')

        view_button = View()
        view_button.add_item(hit)
        view_button.add_item(stand)

        disable_view = View()
        disable_view.add_item(deal)

        new_view = View()
        new_view.add_item(replay)
        new_view.add_item(double)
        new_view.add_item(quit)

        dealer = []
        player = []

        dealer.append(random.randint(1, 13))
        dealer.append('x')

        player.append(random.randint(1, 13))
        player.append(random.randint(1, 13))

        while (get_score(player) >= 21):
          player = [random.randint(1, 13), random.randint(1, 13)]

        await message.channel.send(
            f"Dealer's cards: {dealer} \n{user.display_name}'s cards: {player}"
            + f"\t {user.display_name} score: " + str(get_score(player)))

        if (get_score(player) == 21):
          await message.channel.send(f"{user.display_name} win!")
          user_data[user] = user_data[user] + 100 * mult
          await message.channel.send(
              f"{user.display_name} has {user_data[user]} tokens!")
          await message.channel.send(view=new_view)
        else:
          await message.channel.send(view=view_button)

          ###hit button###
          async def on_hit_click(interaction):
            nonlocal hit, stand
            await interaction.message.edit(view=disable_view)

            await interaction.response.send_message("hit")
            player.append(random.randint(1, 13))
            await message.channel.send(
                f"Dealer's cards: {dealer} \n{user.display_name}'s cards: {player}"
                + f"\t {user.display_name} score: " + str(get_score(player)))
            if (get_score(player) > 21):
              await message.channel.send(f"{user.display_name} lost!")
              double.disabled = True
              user_data[user] = user_data[user] - 100 * mult
              global count
              count = 1
              await message.channel.send(
                  f"{user.display_name} has {user_data[user]} tokens!")
              if (user_data[user] <= 0):
                replay.disabled = True
              await message.channel.send(view=new_view)

            elif (get_score(player) == 21):
              await message.channel.send(f"{user.display_name} won!")
              user_data[user] = user_data[user] + 100 * mult
              await message.channel.send(
                  f"{user.display_name} has {user_data[user]} tokens!")
              await message.channel.send(view=new_view)
            else:
              await message.channel.send("Hit or Stand?", view=view_button)

          ###stand button###
          async def on_stand_click(interaction):
            global count
            await interaction.message.edit(view=disable_view)
            await interaction.response.send_message("stand")
            dealer[1] = random.randint(1, 13)
            while (get_score(dealer) < 17):
              dealer.append(random.randint(1, 13))
            await message.channel.send(
                f"Dealer's cards: {dealer}" + "\t dealer score: " +
                str(get_score(dealer)) +
                f"\n{user.display_name}'s cards: {player}" +
                f"\t {user.display_name} score: " + str(get_score(player)))
            if (get_score(dealer) > 21) or (21 - get_score(dealer) >
                                            21 - get_score(player)):
              await message.channel.send(f"{user.display_name} won!")
              user_data[user] = user_data[user] + 100 * mult
              await message.channel.send(
                  f"{user.display_name} has {user_data[user]} tokens!")
              await message.channel.send(view=new_view)

            elif (get_score(dealer)
                  == 21) or (21 - get_score(dealer) < 21 - get_score(player)):
              await message.channel.send(f"{user.display_name} lost!")
              double.disabled = True
              user_data[user] = user_data[user] - 100 * mult
              count = 1
              await message.channel.send(
                  f"{user.display_name} has {user_data[user]} tokens!")
              if (user_data[user] <= 0):
                replay.disabled = True

              await message.channel.send(view=new_view)

            elif (get_score(dealer) == get_score(player)):
              await message.channel.send(f"{user.display_name} tied!")
              await message.channel.send(
                  f"{user.display_name} has {user_data[user]} tokens!")
              double.disabled = True
              global tie
              tie = True

              await message.channel.send(view=new_view)
            else:
              await message.channel.send("Unexpected")
              await message.channel.send(view=new_view)

          ###double###
          async def on_double_click(interaction):
            global count
            count *= 2
            await on_black_click(interaction, count)

          ###replay###
          async def on_replay_click(interaction):
            global count
            global tie
            if tie:
              tie = False
              await on_black_click(interaction, count)
            else:
              await on_black_click(interaction, 1)

          ###quit button###
          async def on_quit_click(interaction):
            await interaction.response.send_message("Quit")
            replay.disabled = True
            double.disabled = True
            quit.disabled = True
            await interaction.message.edit(view=new_view)

          replay.callback = on_replay_click
          double.callback = on_double_click
          quit.callback = on_quit_click

          hit.callback = on_hit_click
          stand.callback = on_stand_click

    ###Slotmachine###
    async def on_slot_click(interaction):
      user = interaction.user
      if user not in user_data:
        user_data[user] = 100

        money.disabled = True
        black.disabled = True
        slot.disabled = True
        await interaction.message.edit(view=view)

      money.disabled = True
      black.disabled = True
      slot.disabled = True
      await interaction.message.edit(view=view)
      await interaction.response.send_message("You clicked Slot Machine")

      spin = Button(label='Spin!',
                    style=discord.ButtonStyle.green,
                    disabled=False)
      quit = Button(label='Quit',
                    style=discord.ButtonStyle.red,
                    disabled=False)
      slot_view = View()
      slot_view.add_item(spin)
      slot_view.add_item(quit)
      await message.channel.send(view=slot_view)

      async def on_spin_click(interaction):
        spin.disabled = True
        quit.disabled = True
        await interaction.message.edit(view=slot_view)

        colors = [
            0xFF0000, 0xFF7F00, 0xFFFF00, 0x00FF00, 0x0000FF, 0x4B0082,
            0x9400D3
        ]  # Rainbow colors
        slot_embed = Embed(title="Slot Machine is spinning...",
                           description="",
                           color=colors[0])
        await interaction.response.send_message("Spin!")
        message = await interaction.followup.send(embed=slot_embed)

        spin_flag = True  # Set to False when spinning stops

        async def change_color():
          while spin_flag:
            for color in colors:
              slot_embed.color = color
              await message.edit(embed=slot_embed)
              time.sleep(1)

        color_task = client.loop.create_task(change_color())

        slot_arr = ['🍓', '💰', '⭐', '🍏', '💙', '🟣']

        reel1 = Button(emoji=slot_arr[0], disabled=True)
        reel2 = Button(emoji=slot_arr[1], disabled=True)
        reel3 = Button(emoji=slot_arr[2], disabled=True)
        reel4 = Button(emoji=slot_arr[3], disabled=True)
        reel5 = Button(emoji=slot_arr[4], disabled=True)

        button_view = View()
        button_view.add_item(reel1)
        button_view.add_item(reel2)
        button_view.add_item(reel3)
        button_view.add_item(reel4)
        button_view.add_item(reel5)

        async def change_icon(button, count, button_view, interaction):
          slot_arr = ['🍓', '💰', '⭐', '🍏', '💙', '🟣']
          for i in range(count):
            button.emoji = slot_arr[i % len(slot_arr)]
            await interaction.message.edit(view=button_view)
            time.sleep(1)

        tasks = [
            change_icon(reel1, 4 + random.randint(0, 6), button_view,
                        interaction),
            change_icon(reel2, 3 + random.randint(0, 6), button_view,
                        interaction),
            change_icon(reel3, 2 + random.randint(0, 6), button_view,
                        interaction),
            change_icon(reel4, 1 + random.randint(0, 6), button_view,
                        interaction),
            change_icon(reel5, random.randint(0, 6), button_view, interaction)
        ]
        await asyncio.gather(*tasks)

        spin_flag = False  # Stop changing the embed color
        await color_task
        slot_embed.color = 0xFFC0CB
        slot_embed.title = "Spinning stopped"
        await message.edit(embed=slot_embed)

        icon1 = reel1.emoji
        icon2 = reel2.emoji
        icon3 = reel3.emoji
        icon4 = reel4.emoji
        icon5 = reel5.emoji

        icon_list = [icon1, icon2, icon3, icon4, icon5]
        reel_list = [reel1, reel2, reel3, reel4, reel5]

        def find_max_occurrence_indexes(arr):
          occurrences = {}  # Dictionary to store item occurrences
          max_occurrences = 0  # Initialize maximum occurrence count

          for i, item in enumerate(arr):
            if item in occurrences:
              occurrences[item].append(i)
            else:
              occurrences[item] = [i]

            max_occurrences = max(max_occurrences, len(occurrences[item]))

          # Find items with the maximum occurrence count
          max_occurrence_items = [
              item for item, indexes in occurrences.items()
              if len(indexes) == max_occurrences
          ]

          if len(max_occurrence_items) > 1:
            # If there's a tie, return the first one
            max_occurrence_items = [max_occurrence_items[0]]

          max_occurrence_indexes = occurrences[max_occurrence_items[0]]

          return max_occurrence_indexes

        duplicates = find_max_occurrence_indexes(icon_list)

        if len(duplicates) == 1:

          reel1.style = discord.ButtonStyle.red
          await interaction.message.edit(view=button_view)
          reel2.style = discord.ButtonStyle.red
          await interaction.message.edit(view=button_view)
          reel3.style = discord.ButtonStyle.red
          await interaction.message.edit(view=button_view)
          reel4.style = discord.ButtonStyle.red
          await interaction.message.edit(view=button_view)
          reel5.style = discord.ButtonStyle.red
          await interaction.message.edit(view=button_view)

          await message.channel.send(f"{user.display_name} lost!")
          user_data[user] = 0
          await message.channel.send(f"{user.display_name} now have 0 token")

        elif len(duplicates) > 1 and len(duplicates) < 5:
          for i in duplicates:
            reel_list[i].style = discord.ButtonStyle.green
            await interaction.message.edit(view=button_view)

          count = len(duplicates)
          user_data[user] = user_data[user] + 50 * (count - 1)

          await message.channel.send(f"{user.display_name} won!")
          await message.channel.send(
              f"{user.display_name} now have {user_data[user]} token")

        elif len(duplicates) == 5:
          reel1.style = discord.ButtonStyle.green
          await interaction.message.edit(view=button_view)
          reel2.style = discord.ButtonStyle.green
          await interaction.message.edit(view=button_view)
          reel3.style = discord.ButtonStyle.green
          await interaction.message.edit(view=button_view)
          reel4.style = discord.ButtonStyle.green
          await interaction.message.edit(view=button_view)
          reel5.style = discord.ButtonStyle.green
          await interaction.message.edit(view=button_view)
          await message.channel.send("JACKPOT!!!")
          user_data[user] = user_data[user] + 100 * 10
          await message.channel.send(
              f"{user.display_name} now have {user_data[user]} token")

      async def on_quit_click(interaction):
        await interaction.response.send_message("You clicked Quit")
        spin.disabled = True
        quit.disabled = True
        await interaction.message.edit(view=slot_view)

      spin.callback = on_spin_click
      quit.callback = on_quit_click

    black.callback = lambda interaction: on_black_click(interaction, 1)
    slot.callback = on_slot_click
    stock.callback = on_stock_click


keep_alive()
my_secret = os.environ['TOKEN']
client.run(my_secret)
