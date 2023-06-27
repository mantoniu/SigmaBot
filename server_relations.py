import json

def read_corrected_results() -> dict:
    with open("data/corrected_results.txt","r") as f:
        return json.loads(f.read())

def save_corrected_results(corrected_results: dict) -> None:
    with open("data/corrected_results.txt","w") as f:
        json.dump(corrected_results,f)

def sentence_in_correctedresults(sentence: list, corrected_results: dict) -> int:
    res = - 1
    for i in range(len(corrected_results[sentence[0]])):
        data_dict = corrected_results[sentence[0]][i]
        if data_dict["name"]==sentence[2] and data_dict["rel"]==sentence[1]:
            res = i
    return res

def bad_JDM_response(sentence: list, correct_res: bool) -> None:
    corrected_results = read_corrected_results()

    if sentence[0] in corrected_results.keys():
        res = sentence_in_correctedresults(sentence,corrected_results)
        if res != -1:
            if correct_res:
                corrected_results[sentence[0]][res]["weight"] += 1
            else:
                corrected_results[sentence[0]][res]["weight"] -= 1
        else:
            corrected_results[sentence[0]].append({"name":sentence[2],"rel":sentence[1],"weight":1 if correct_res else -1})

    else:
        corrected_results[sentence[0]] = [{"name":sentence[2],"rel":sentence[1],"weight":1 if correct_res else -1}]

    save_corrected_results(corrected_results)


def corrected_valitidy(sentence: list) -> bool:
    corrected_results = read_corrected_results()
    print(sentence)
    if sentence[0] in corrected_results.keys():
        res = sentence_in_correctedresults(sentence,corrected_results)
        if res!=-1:
            weight = corrected_results[sentence[0]][res]["weight"] 
            if weight>=5:
                return True,sentence[0],sentence[2]
            elif weight<=-5:
                return False,corrected_results[sentence[0]][res]["name"],sentence[2]

    return False,None

