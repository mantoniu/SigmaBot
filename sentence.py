import spacy
import pickle
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from patterns_list import pattern_dict
import re
import json
import pickle

nlp = nlp = spacy.load("fr_core_news_sm")
stopWords = set(stopwords.words('french'))
types_dict = {}

with open("data/types_dict","rb") as fp:
    types_dict = pickle.load(fp)

with open("data/patterns.txt","r") as f:
    data = f.read()

relation_patterns = json.loads(data)


def add_pattern(relation: str, pattern: str) -> None:
    pattern = sentence_to_pattern(pattern)
    if relation in types_dict.keys():
        relation_number = types_dict[relation]
        if relation_number not in relation_patterns.keys():
            relation_patterns[relation_number]=[pattern]
        else:
            if pattern not in relation_patterns[relation_number]:
                relation_patterns[relation_number].append(pattern)
                relation_patterns[relation_number].sort(reverse=True,key=len)
        with open("data/patterns.txt","w") as file:
            json.dump(relation_patterns,file)

def replace_determinants(sentence: str) -> str:
    pattern = r"(un |une |des )"

    texte_modifie = re.sub(pattern, "(un |une |des )?", sentence)
    return texte_modifie

def sentence_to_pattern(sentence: str) -> str:

    
    # Si lettre finale correspond à une ponctuation remplacer par (ponctuation|\s*)

    final_ponctuation = sentence[len(sentence)-1]
    if final_ponctuation=="?" or final_ponctuation=="." or final_ponctuation=="!":
        sentence = sentence[0:len(sentence)-2]+"( )?(\s*|( )?\\\\"+final_ponctuation+")"

    first_char = sentence[0]
    if first_char.isupper() and first_char!="(":
        sentence = "("+first_char+"|"+first_char.lower()+")"+sentence[1:len(sentence)]
    
    #Si ponctuation dans le reste de la phrase remplacer par (ponctuation| )
    sentence = sentence.replace("-","("+"-"+"| )")
    sentence = sentence.replace("'","("+"'"+"| )")
    sentence = sentence.replace("(E|e)st(-| )ce que ","((E|e)st(-| )ce (que|qu('| )))?")
    sentence = replace_determinants(sentence)
    sentence = sentence.replace("[x]","(?P<x>[^\\?]*)").replace("[y]","(?P<y>[^\\?]*)")
    return sentence


def detect_patterns(sentence):
    max_pattern = 0
    matched_pattern = None
    for relation in relation_patterns.keys():
        for pattern in relation_patterns[relation]:
            match = re.match(pattern, sentence)
            if match and len(pattern)>max_pattern:
                max_relation = relation
                matched_pattern = match
                max_pattern = len(pattern)
                print(pattern)

    if matched_pattern:
        x = matched_pattern.group("x")
        y = matched_pattern.group("y")
        if y[len(y)-1]==" ":
            y = y[0:len(y)-1]
        return [x,int(max_relation),y]
            
def detect_negation(sentence: str) -> tuple:
    negative_words = ["ne","pas","n'"]
    sentence = nlp(sentence)
    res = False
    s_without_negation = ""

    for token in sentence:
        word = token.text
        if word in negative_words:
            res = True
        else:
            s_without_negation += word+" " 

    return res,s_without_negation[0:len(s_without_negation)-1]
            

def delete_stopword(sentence: str): 
    res = ""

    for word in sentence.split():
        if word.lower() not in stopWords:
            res += word+" "

    return res


for relation,sentences in pattern_dict.items():
    for sentence in sentences:
        add_pattern(relation,sentence)


for simple in types_dict.keys():
    add_pattern(simple,"[x] "+simple+" [y]")
