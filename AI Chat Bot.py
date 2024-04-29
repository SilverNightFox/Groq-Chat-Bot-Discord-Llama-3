import os
import sqlite3
import discord
from discord.ext import commands
from groq import Groq
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import numpy as np

# Set up the Discord bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Set up the Groq API client
api_key = 'your-grop-api-key-here'
os.environ['GROQ_API_KEY'] = api_key
client = Groq()

# Initialize a connection to the SQLite database
conn = sqlite3.connect('conversation_history.db')
c = conn.cursor()

# Create a table to store the conversation history for each user
c.execute('''CREATE TABLE IF NOT EXISTS conversation_history
             (user_id INTEGER PRIMARY KEY, history TEXT)''')

# Load the conversation history from the database
@bot.event
async def on_message(message):
    # Check if the message mentions the bot
    if message.mentions and message.mentions[0] == bot.user:
        # Retrieve the user's conversation history from the database
        c.execute("SELECT history FROM conversation_history WHERE user_id=?", (message.author.id,))
        history = c.fetchone()
        if history is not None:
            history = history[0].split('\n')
            # Load the conversation history into NLTK
            conversation = [word_tokenize(message) for message in history]
            # Get the current message
            current_message = word_tokenize(message.content)
            # Calculate the similarity between the current message and each message in the conversation history
            similarities = [sum(current_message.count(word) for word in message) for message in conversation]
            # Find the most similar messages to the current message
            most_relevant_indices = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)[:3]
            most_relevant_history = [history[index] for index in most_relevant_indices]
        else:
            most_relevant_history = []

        # Add the current message to the conversation history
        most_relevant_history.append(message.content)

        # Use the conversation history to generate a response
        prompt = "\n".join(most_relevant_history)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama3-70b-8192",
        )
        response = chat_completion.choices[0].message.content

        # Send the response back to the Discord channel
        await message.channel.send(response)

        # Update the conversation history in the database
        c.execute("REPLACE INTO conversation_history (user_id, history) VALUES (?, ?)", (message.author.id, '\n'.join(most_relevant_history)))
        conn.commit()

bot.run('your-discord-bot-token-here')