import os
import hashlib
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from datetime import datetime
from os.path import exists, getmtime
from time import sleep, time

import pickle
import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter,Retry,ReadTimeoutError

types_dict = {}

with open("data/types_dict","rb") as fp:
    types_dict = pickle.load(fp)

from JDM_objects import Relation_Types, Request_Types, Search_Types, Data_Type
from server_relations import corrected_valitidy

def url_encode_plus(word: str) -> str:
    return urllib.parse.quote_plus(word.encode("cp1252")).replace("/","%2F")

def lastmodification_date(path: str) -> datetime:
    return datetime.fromtimestamp(getmtime(path))

def oneweek_between(date1 : datetime, date2 : datetime) -> bool:
    return (date1-date2).days>=7


def cut_dataJDM(html :str, start : str, end: str) -> str:
    start_i = html.find(start)
    end_i = html.rfind(end)
    return html[start_i+len(start):end_i]

def word_to_md5(word: str) -> str:
    return hashlib.md5(word.encode()).hexdigest()

def save(path: str, data: str):
    with open(path,"w",encoding="utf-8") as data_file:
        data_file.write(data)

def file_exists_case_sensitive(file_path):
    directory = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)

    files = os.listdir(directory)
    for file in files:
        if file == file_name:
            return True

    return False

def names_by_nodes(nodes: pd.DataFrame) -> list:
    return nodes["name"].values

def jdm_request(converted_word: str, relation: int, request_type: Request_Types) -> str:
    s = requests.Session()

    retries = Retry(total=50,
            backoff_factor=1,
            status_forcelist=[ 429 ,500, 502, 503, 504 ])
    
    s.mount('http://', HTTPAdapter(max_retries=retries))

    return s.get('https://www.jeuxdemots.org/rezo-dump.php?gotermsubmit=Chercher&gotermrel='+converted_word+'&rel='+str(relation)+request_type.value).text 

def save_word_data(word: str, relation: int, request_type: Request_Types) -> None:
    converted_word = url_encode_plus(word)
    word_md5 = word_to_md5(word)
    if request_type == Request_Types.OUTGOING:
        path = "saves/"+converted_word+"-ro"+str(relation)+"nodes"+" - "+word_md5+".csv"
    else:
        path = "saves/"+converted_word+"-ri"+str(relation)+"nodes"+" - "+word_md5+".csv"
    if not(exists(path)) or oneweek_between(datetime.now(),lastmodification_date(path)):  
        #print(f"Enregistrement de {word} ...")
        html = jdm_request(converted_word,relation,request_type) 

        if html.find("MUTED")!=-1 or html.find("Le terme '"+word+"' n'existe pas !")!=-1:
            return -1
        
        nodes_data = cut_dataJDM(html,"(Entries) : ","// les types de relations (Relation Types) : ")

        if request_type == Request_Types.OUTGOING:
            rel_data = cut_dataJDM(html,"relations sortantes : ","// END")
            save(path,nodes_data)
            save("saves/"+converted_word+"-ro"+str(relation)+" - "+word_md5+".csv",rel_data)

        else:
            rel_data = cut_dataJDM(html,"// les relations entrantes :","// END")
            save(path,nodes_data)
            save("saves/"+converted_word+"-ri"+str(relation)+" - "+word_md5+".csv",rel_data)

def save_data(wordlist: list, relation: int, request_type: Request_Types):
    futures = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(save_word_data,word,relation, request_type) for word in wordlist]
        wait(futures)
        for future in futures:
            if future.result()==-1:
                return -1


def read_csv_data(path: str) -> pd.DataFrame:
    try:
        res = pd.read_csv(path,delimiter=";",quotechar="'",on_bad_lines='skip')
    except:
        res = None
        print("Pas de colonne à lire")
    return res

def read_word_rel(word: str, rel: int, request_type: Request_Types, data_type : Data_Type):
    word_c = url_encode_plus(word)
    word_md5 = word_to_md5(word)

    if request_type == Request_Types.OUTGOING:
        return read_csv_data("saves/"+word_c+"-ro"+str(rel)+("nodes" if data_type == Data_Type.NODES else "")+" - "+word_md5+".csv")
    else:
        return read_csv_data("saves/"+word_c+"-ri"+str(rel)+("nodes" if data_type == Data_Type.NODES else "")+" - "+word_md5+".csv")

def names_with_eids(nodes_data: pd.DataFrame, eids: list, size: int) -> list:
    names = []
    i=0
    while len(names)<size and i<len(eids):
        eid = eids[i]
        nodes = nodes_data[nodes_data["eid"]==eid]["name"].values
        if len(nodes)==0:
            break
        name = nodes.item()
        if name[len(name)-1]!="'" and name not in names and name!="'name'":
            names.append(name)
        i+=1
    return names


def research_relation(word: str, obj: str, relation: str, request_type: Request_Types) -> bool:
    if save_word_data(word,relation,request_type) == -1:
        return -1
    if word=="'name'":
        return False,None
    
    #print("mot",word)

    nodes_st = read_word_rel(word,relation,request_type,Data_Type.NODES)
    r_data = read_word_rel(word,relation,request_type,Data_Type.REL)

    try:
        if obj in nodes_st["name"].values: 
            objid = nodes_st[nodes_st["name"]==obj]['eid'].item()
            rs_data_weight = r_data[r_data["w "]>0]
            if objid in r_data["node2"].values:
                if objid in rs_data_weight["node2"].values:
                    return True,word,obj
                else:
                    return False,word,obj
    except:
        print("Erreur de lecture du fichier")

    return False,None


def research_with_names(names: list, obj: str, relation: str) -> bool:
    futures = []
    with ThreadPoolExecutor(max_workers=len(names)) as executor:
            futures = [executor.submit(research_relation,word,obj,relation,Request_Types.OUTGOING) for word in names]

            for future in as_completed(futures):
                res = future.result()
                if res == -1:
                    return -1
                if res[1] != None:
                    return res[0],res[1],res[2]
    return False,None


def research(subject: str, relation: int, obj: str, search_type: Search_Types) -> bool:
    #print(subject,relation,obj,search_type)

    ## Renvoyer False quand DEDUCTION + r_hyp

    if search_type == Search_Types.DEDUCTION and relation == Relation_Types.r_hypo.value:
        return False,None
    
    if search_type == Search_Types.INDUCTION and relation == int(Relation_Types.r_hypo.value):
        relation = int(Relation_Types.r_isa.value)

    match search_type:
        case Search_Types.INDUCTION:
            search_type_rel = "6"
            request_type = Request_Types.INGOING
            node = "node1"

        case _:
            if type(search_type)==Search_Types:
                search_type_rel = search_type.value
            else:
                search_type_rel = search_type
            request_type = Request_Types.OUTGOING
            node = "node2"


    nodes_isa_data = read_word_rel(subject,search_type_rel,request_type,Data_Type.NODES)
    r_isa_data = read_word_rel(subject,search_type_rel,request_type,Data_Type.REL)

    if not(type(nodes_isa_data)==pd.DataFrame) or not(type(r_isa_data)==pd.DataFrame):
        return -1

    eids = r_isa_data[r_isa_data["w "]>50][node].values

    names = names_with_eids(nodes_isa_data,eids,50)

    if len(names)==0:
        return False,None
    
    #Sprint(search_type,names)
    # if save_data(names,relation, Request_Types.OUTGOING)==-1:
    #     print("ERREUR LORS DE LA SAUVEGARDE \n")
    #     return -1
    research_res = research_with_names(names,obj,relation)

    if research_res==-1:
        return -1
    
    return research_res


def save_word_relations(word: str, relations: list) -> None:
    futures = []
    with ThreadPoolExecutor(max_workers=len(relations)) as executor:
        futures = [executor.submit(save_word_data,word,relation,request_type) for request_type,relation in relations]
        wait(futures)
        for future in futures:
            if future.result()==-1:
                return -1

def nodes_name_with_relation(word :str,relation: int, ceil: int) -> list:
    nodes = read_word_rel(word,relation,Request_Types.OUTGOING,Data_Type.NODES)
    r = read_word_rel(word,relation,Request_Types.OUTGOING,Data_Type.REL)
    r = r[r["w "]>ceil]["node2"].values
    nodes = nodes[nodes["eid"].isin(r)]["name"].values
    return nodes

def get_refinement(word: str) -> str:
    if type(word)==str and word.find(">")!=-1:
        return word.split(">")[1]
    return ""

def semantic_refinements(subject:str, word: str) -> list:
    ## Téléchargement des données
    if save_word_relations(subject,[(Request_Types.OUTGOING,0),(Request_Types.OUTGOING,24)]) == -1:
        return -1
    if save_word_relations(word,[(Request_Types.OUTGOING,1),(Request_Types.OUTGOING,0)]) == -1:
        return -1

    ## Lecture des raffinements + Lecture des associés

    nodes = read_word_rel(word,Relation_Types.r_raff_sem.value,Request_Types.OUTGOING,Data_Type.NODES)

    ## Obtention de tous les raffinements
    nodes = nodes[nodes["name"]!=word]
    refinements_dict = pd.Series(nodes["name"].values,index=nodes["formated name "]).to_dict()
    refinements_dict[word+">sens générique"] = word

    ## Obtention des associés et agent-1 avec poids >10
    subject_nodes_associated = nodes_name_with_relation(subject,relation=0,ceil=30)
    # nodes_agent_1 = nodes_name_with_relation(subject_md5,subject_c,24,10


    for refinement in refinements_dict.values():
        if refinement in subject_nodes_associated: # refinement in nodes_agent_1:
            return refinement
        
    for refinement in list(refinements_dict.keys()):
        if type(refinement)==float:
            del refinements_dict[refinement]
        ref = get_refinement(refinement)
        if ref in subject_nodes_associated:
            return word

    return refinements_dict


def double_rel_research(word: str, subject: str, relation: int, relation_search: int) -> list:
    ## Lecture de la relation des deux mots
    word_nodes = read_word_rel(word,relation_search,Request_Types.OUTGOING,Data_Type.NODES)

    save_word_data(subject,Relation_Types.r_syn.value,Request_Types.OUTGOING)

    subject_nodes = read_word_rel(subject,relation_search,Request_Types.OUTGOING,Data_Type.NODES)

    word_names = word_nodes["name"].values
    subject_names = subject_nodes["name"].values

    if len(word_names)>20:
        word_names = word_names[0:19]
    if len(subject_names)>20:
        subject_names = subject_names[0:19]

    #print(word_names)
    #print(subject_names)

    with ThreadPoolExecutor(max_workers=len(word_names)) as executor:
        futures = [executor.submit(research_with_names,word_names,subject,relation) for subject in subject_names]

        for future in as_completed(futures):
            res = future.result()
            if res == -1:
                return -1
            elif res[1] != None:
                return res

    return False,None    


def sentence_validity(sentence: list) -> list:
    subject, relation, obj = sentence[0], sentence[1], sentence[2]

    # Obtention des données des deux mots 
    relations = [(Request_Types.OUTGOING,6),(Request_Types.INGOING,6),(Request_Types.OUTGOING,relation),(Request_Types.OUTGOING,Search_Types.SYNONYMUM.value)]
    if save_word_relations(subject,relations) == -1:
        return -1

    # Vérification réponse dans base serveur
    corrected_response = corrected_valitidy(sentence)


    if corrected_response[1] != None:
        print(corrected_response)
        return ["bdd",corrected_response]

    # Vérification réponse dans relation directe 

    if relation == int(Relation_Types.r_hypo.value):
        res = research_relation(subject,obj,int(Relation_Types.r_isa.value),Request_Types.OUTGOING)
    else:
        res = research_relation(subject,obj,relation,Request_Types.OUTGOING)


    if res[1] != None:
        return ["direct",res]

    # Vérification dans isa (déduction)/ hypo (induction)

    with ThreadPoolExecutor(max_workers=3) as executor:
        deduction = executor.submit(research,subject,relation,obj,Search_Types.DEDUCTION)
        induction = executor.submit(research,subject,relation,obj,Search_Types.INDUCTION)
        # synonyme = executor.submit(double_rel_research,subject,obj,relation,Search_Types.SYNONYMUM.value)

        wait([deduction])
        deduction_res = deduction.result()
        if deduction_res == -1:
            return -1
        if deduction_res[1] != None:
            print("déduction")
            return ["r_isa",deduction_res]
        else:
            wait([induction])
            induction_res = induction.result()
            if induction_res == -1:
                return -1
            if induction_res[1] != None:
                print("induction")
                return ["r_hypo",induction_res]

    synonymum_res = double_rel_research(subject,obj,relation,Search_Types.SYNONYMUM.value)
    if synonymum_res == -1:
        return -1
    if synonymum_res[1] == None and relation==int(Relation_Types.r_lieu.value):
        return sentence_validity([sentence[2],int(Relation_Types.r_has_part.value),sentence[0]])
    else:
        return ["r_syn",synonymum_res]

   
start_time = time()
print("--- %s seconds ---" % (time() - start_time))


def search_good_rel(word: str, subject: str, rel: int, max_rel: int) -> list:
    all_rel = [int(r.value) for r in Relation_Types]
    find_num = 0
    i = 0
    results = []
    while find_num!=max_rel and i<len(all_rel):
        relation = all_rel[i]
        res = research(word,rel,subject,relation)
        if res!=-1 and res[0]==True:
            find_num +=1
            results.append([[k for k, v in types_dict.items() if v == str(relation)][0],res])
        i+=1
    return results



def other_relations_between(subject: str, object: str) -> list:
    for relation1 in range(0,32):
        save_word_data(subject,relation1,Request_Types.OUTGOING)
        nodes = read_word_rel(subject,relation1,Request_Types.OUTGOING,Data_Type.NODES)
        names = names_by_nodes(nodes)

        for name in names:
            for relation2 in range(0,32):
                if name.find("_")==-1 or name.find("::"):
                    save_word_data(name,relation2,Request_Types.OUTGOING)
                    res =research_relation(name,object,relation2,Request_Types.OUTGOING)
                    if res[1] != None:
                        return relation1,relation2,name,res

        print(relation1,names)




## Homme r_lieu restaurant oui car homme r_agent-1 manger et manger r_lieu restaurant