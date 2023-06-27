from random import randint
import sentence
import dataJDM
from bot_objects import Bot_Status


def text_response(negative: bool, search_type: str, converted_s: list, res: list) -> str:
    if negative and res[0] or not(negative) and not(res[0]):
        start = "C'est faux" 
    elif negative and not(res[0]) or not(negative) and res[0]:
        start = "C'est vrai"

    if res[1]==None:
        return start+" car aucune relation n'a été trouvée !",(converted_s,res[0])

    else:
        if res[2]!=converted_s[2]:
            converted_s[2] = res[2]+" qui "+search_type+" "+converted_s[2] 
        rel_negative = ""
        if not(res[0]) and res[1]!=None:
            rel_negative = " mais avec un poids négatif"
        match search_type:
                case "direct"|"bdd":
                    return start +" car "+converted_s[0]+" est en relation directe "+[k for k, v in sentence.types_dict.items() if v == str(converted_s[1])][0]+ " avec "+converted_s[2]+rel_negative+" ! 🗿🗿",(converted_s,res[0])
                case _:
                    return start +" car "+converted_s[0]+" "+search_type+" "+res[1]+" et "+res[1]+" possède la relation "+  [k for k, v in sentence.types_dict.items() if v == str(converted_s[1])][0] +" avec "+converted_s[2]+rel_negative+" !  🗿🗿",(converted_s,res[0])


def handle_response(user_message: str, bot_statut : Bot_Status) -> tuple:
    if bot_statut == None:
        negative = sentence.detect_negation(user_message)
        explanation = False
        if negative[0]:
            user_message = negative[1]    

        if user_message.startswith("pq"):
            user_message = user_message[3:len(user_message)]
            explanation = True

        converted_s = sentence.detect_patterns(user_message)

        print("Conversion : ", converted_s)

        if converted_s == None:
            return Bot_Status.PATTERN_ERROR

        ### Vérification si plusieurs sens

        semantic_refinements = dataJDM.semantic_refinements(converted_s[0],converted_s[2])
        print(semantic_refinements)

        if semantic_refinements == -1:
            return Bot_Status.WORD_NOT_FOUND

        return Bot_Status.ASK_REFINEMENTS,[converted_s,negative,explanation],semantic_refinements
    
    else:
        print(user_message)
        explanation = user_message[2]            
        print(user_message)

        converted_s = user_message[0]
        print(converted_s)
        negative = user_message[1]

        if explanation:
            results = dataJDM.search_good_rel(converted_s[0],converted_s[2],converted_s[1],3)

            if not(results):
                return "Aucune explication n'a été trouvée !",False

            res_text = ""

            for res in results:
                print(text_response(negative[0],res[0],converted_s,res[1])[0])
                res_text += text_response(negative[0],res[0],converted_s,res[1])[0] + "\n"
            

            return res_text,False

        else:

            result = dataJDM.sentence_validity(converted_s)

            print("Résultat ",result)

            res = result[1]

            search_type = result[0]        

            if result==-1:
                return Bot_Status.WORD_NOT_FOUND

           
            
            return text_response(negative[0],search_type,converted_s,res)

