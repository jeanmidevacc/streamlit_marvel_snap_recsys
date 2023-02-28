import streamlit as st
import base64

import pandas as pd
import numpy as np

import requests
from bs4 import BeautifulSoup as bs

# Build general/cachec variables
@st.cache_data
def cache_dfp_cards():
    dfp_cards = pd.read_csv("./data/cards.csv")
    dfp_cards["card"] = dfp_cards["carddefid"]
    dfp_cards = dfp_cards.set_index(["carddefid"])
    dfp_cards["coefficient_winrate"] = dfp_cards["stats_winrate"]
    return dfp_cards
dfp_cards = cache_dfp_cards()
carddefids = dfp_cards.index.tolist()

@st.cache_data
def cache_associations():
    associations = {}
    for delta_days in [-1, 7, 30]:
        associations[delta_days] = pd.read_csv(f"./data/association_norm_{delta_days}.csv").set_index("Unnamed: 0")
    
    associations[0] = pd.read_csv(f"./data/association_win_rate.csv").set_index("Unnamed: 0")
    return associations
associations = cache_associations()

def get_cards_user(username_msz):
    url_user = f"https://marvelsnapzone.com/users/{username_msz}/"
    response = requests.get(url_user)
    soup = bs(response.content,features = "html.parser")
    cids = sorted([int(elt["data-cid"]) for elt in soup.find_all("a", {"class" : "card-collection collected"})])
    if len(cids) == 0:
        return False, carddefids
    else:
        return True, dfp_cards[dfp_cards["cid"].isin(cids)].index.tolist()

mapping_time_period = {
    'All time' : -1,
    'Last 7 days' : 7,
    'Last 30 days' : 30
}

def build_recommendations(time_period, associations, inventory, main_cards, coefficient=0):
    dfp_recommendations = associations[mapping_time_period[time_period]][main_cards].sum(axis=1).sort_values(ascending=False).to_frame().reset_index()
    dfp_recommendations.columns = ["card", "score"]
    dfp_recommendations = dfp_recommendations[dfp_recommendations["card"].isin(inventory)]
    dfp_recommendations = pd.merge(dfp_recommendations, dfp_cards[["card", "cost", "power", "coefficient_winrate"]], on="card")

    if coefficient > 0:
        dfp_recommendations["score"] = dfp_recommendations.apply(lambda row: row["score"] * coefficient * (1 + row["coefficient_winrate"]), axis=1)
    
    dfp_recommendations = dfp_recommendations[(dfp_recommendations["score"] > 0) & (dfp_recommendations["card"].isin(main_cards) == False)]
    return dfp_recommendations[["card", "score", "cost", "power"]]

def build_recommendations_new_gen(time_period, associations, inventory, main_cards, coefficient=0):
    dfp_recommendations_association_wr = associations[0][main_cards].mean(axis=1).sort_values(ascending=False).to_frame().reset_index()
    dfp_recommendations_association_wr.columns = ["card", "score"]
    dfp_recommendations_association_wr = dfp_recommendations_association_wr[dfp_recommendations_association_wr["card"].isin(inventory)]
    dfp_recommendations_association_wr = pd.merge(dfp_recommendations_association_wr, dfp_cards[["card", "cost", "power", "coefficient_winrate"]], on="card")

    dfp_recommendations = dfp_recommendations_association_wr[(dfp_recommendations_association_wr["score"] > 0) & (dfp_recommendations_association_wr["card"].isin(main_cards) == False)]
    return dfp_recommendations[["card", "score", "cost", "power"]]


def build_deck_code(name, deck):
    deck_dict = {"Name" : name, "Cards" : [{"CardDefId":card} for card in deck]}
    deck_dict_str_encode = str(deck_dict).encode('utf-8')
    return base64.b64encode(deck_dict_str_encode).decode("utf-8") 

st.title('Marvel snap deck builder')
st.header("Collect your cards on marvel snap zone")
username_msz = st.text_input("Enter your username")
status_cards, cards = get_cards_user(username_msz)
st.write(f"This is the user cards:", status_cards)
st.write(f"Pool of {len(cards)} cards to pick in :) ")

st.header("Setup your recommender inputs")
deck = st.multiselect(
    "Select your cards",
    cards)
use_only_win_rate = st.checkbox('Use only win rate association', value=True)
encoded_deck = build_deck_code("test", deck)
if len(deck) == 12:
    st.write("the code:")
    st.code(encoded_deck)
elif len(deck) > 12:
    st.write("Too much cards (not more than 12)")
else:
    st.write(f"You need to select {12 - len(deck)} cards")

if not use_only_win_rate:
    time_period = st.radio(
        "Time period for the association",
        ('All time', 'Last 7 days', 'Last 30 days'))
    st.write('You selected the associations:', time_period)
    coefficient = st.slider('Weight of the win rate in the last 7 days', 0, 10, 0)
    dfp_recommendations = build_recommendations_new_gen(time_period, associations, cards, deck, coefficient)
else:
    dfp_recommendations = build_recommendations_new_gen("",associations, cards, deck, 0)

st.header("Recommendations")
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("cost < 3")
    st.table(dfp_recommendations[dfp_recommendations["cost"] < 3].head(3)[["card", "score"]])

with col2:
    st.subheader("cost [3,5[")
    st.table(dfp_recommendations[(dfp_recommendations["cost"] >= 3) &(dfp_recommendations["cost"] < 5)].head(3)[["card", "score"]]) 

with col3:
    st.subheader("cost >= 5")
    st.table(dfp_recommendations[(dfp_recommendations["cost"] >= 5)].head(3)[["card", "score"]]) 

st.header("Your deck")
if len(deck) == 12:
    st.write("Your deck:",  deck)
    st.write("the code:")
    st.code (encoded_deck)

elif len(deck) > 12:
    st.write("Too much cards, you should drop some cards in the main cards and cards selection to not exceed 12")
else:
    st.write("Your deck (incomplete):",  deck)




