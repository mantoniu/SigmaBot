import discord
import responses
from bot_objects import Bot_Status
import server_relations


TOKEN = 'BOT TOKEN'
CLIENT = discord.Client(intents=discord.Intents.all())
CHARACTERS = ['/','?','!'] 

LAST_REQUEST = {}
AWAITING_RESPONSES = {}



async def send_response_and_opinion(message, user_id: str,response: tuple) -> None:
    if response[1]==False:
        await message.channel.send(response[0])
        del AWAITING_RESPONSES[user_id]
    await message.channel.send(response[0])
    LAST_REQUEST[user_id] = response[1]        

    ## Demande de confirmation de la réponse
    await message.channel.send("La réponse est elle bonne ? (réponses possibles : oui,non,nsp)")
    AWAITING_RESPONSES[user_id] = Bot_Status.WAITING_OPINION



async def send_message(message, user_message: str, user_id: str, is_private: bool) -> str:
    try:
        if user_id in AWAITING_RESPONSES:
            if AWAITING_RESPONSES[user_id] == Bot_Status.RECEIVED_REFINEMENT:            
                
                converted = LAST_REQUEST[user_id][0]
                refinements = LAST_REQUEST[user_id][1]
                refinements_keys = list(refinements.keys())
                refinement = refinements_keys[user_message-1]
                user_message = [[converted[0][0],converted[0][1],refinements[refinement]],converted[1],converted[2]]

                del AWAITING_RESPONSES[user_id]
                del LAST_REQUEST[user_id]

                response = responses.handle_response(user_message, Bot_Status.RECEIVED_REFINEMENT)
                await send_response_and_opinion(message, user_id, response)

        else:
            response = responses.handle_response(user_message, None)

            match response:
                case Bot_Status.PATTERN_ERROR:
                    await message.channel.send("Désolé, je n'ai pas bien compris votre demande. Pouvez-vous la reformuler ?")
                    ## Faire commande pour ajouter pattern
                
                case Bot_Status.WORD_NOT_FOUND:
                    await message.channel.send("Désolé, le mot recherché n'a pas été trouvé dans la base de données.")


                case (Bot_Status.ASK_REFINEMENTS,_,_):
                    if type(response[2]) == dict:
                        if len(response[2].keys())<=1:
                            response = responses.handle_response([response[1][0],response[1][1],response[1][2]], Bot_Status.ONE_REFINEMENT)
                            await send_response_and_opinion(message, user_id, response)
                        else:
                            request = "Plusieurs sens pour le mot "+response[1][0][2]+" ont été détéctés : \n"
                            i=0
                            
                            for word in response[2].keys():
                                i+=1
                                request += str(i)+". " + str(word) + "\n"
                            request += "Entrez le numéro du sens que vous souhaitez."
                            LAST_REQUEST[user_id] = (response[1],response[2])
                            AWAITING_RESPONSES[user_id] = Bot_Status.WAITING_REFINEMENT
                            await message.channel.send(request)
                    else:   
                            print(response)
                            user_message = [[response[1][0][0],response[1][0][1],response[2]],response[1][1],response[1][2]]
                            response = responses.handle_response(user_message, Bot_Status.ONE_REFINEMENT)
                            await send_response_and_opinion(message, user_id, response)

    except Exception as e:
        print(e)


def run_discord_bot():
    @CLIENT.event
    async def on_ready():
        await CLIENT.change_presence(activity=discord.Game(name='Roblox RP (mod : girlfriends)'))
        print(f'{CLIENT.user} is now runnning! ')

    @CLIENT.event
    async def on_message(message):
        if message.author == CLIENT.user:
            return 

        if message.channel.name == "sigmabot":        
            username = str(message.author)
            user_message = str(message.content)
            channel = str(message.channel)
            user_id = user_id = message.author.id


            print(f'Message de {username} : {user_id} {user_message} ({channel})\n')

            if user_id in AWAITING_RESPONSES.keys():
                if AWAITING_RESPONSES[user_id] == Bot_Status.WAITING_OPINION:
                    user_message = user_message.lower()

                    match user_message:
                        case "oui":
                            server_relations.bad_JDM_response(LAST_REQUEST[user_id][0],LAST_REQUEST[user_id][1])
                            del AWAITING_RESPONSES[user_id]
                            await message.channel.send("Merci, votre réponse a bien été prise en compte !")
                        case "non":
                            server_relations.bad_JDM_response(LAST_REQUEST[user_id][0],not(LAST_REQUEST[user_id][1]))
                            del AWAITING_RESPONSES[user_id]
                            await message.channel.send("Merci, votre réponse a bien été prise en compte !")
                        case "nsp":
                            del AWAITING_RESPONSES[user_id]
                            await message.channel.send("Merci, votre réponse a bien été prise en compte !")
                        case _:
                            await message.channel.send("Désolé, votre réponse n'a pas été reconnue (réponses autorisées : oui,non,nsp)")
                elif AWAITING_RESPONSES[user_id] == Bot_Status.WAITING_REFINEMENT:
                    if int(user_message)>=1 and int(user_message)<=len(LAST_REQUEST[user_id][1]):
                        AWAITING_RESPONSES[user_id] = Bot_Status.RECEIVED_REFINEMENT
                        await send_message(message, int(user_message), user_id, is_private=False)
                    else:
                        await message.channel.send("Désolé, le raffinement demandé n'est pas disponible !")
            else:
                await send_message(message, user_message, user_id, is_private=False)

    CLIENT.run(TOKEN)
