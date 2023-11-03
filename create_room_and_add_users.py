from ldap3 import Server, Connection, SUBTREE
import requests
import asyncio

# Configuration LDAP
ldap_server = 'ldaps://ldap.epfl.ch:636'
base_dn = 'o=epfl,c=ch'

# Configuration Matrix Synapse
homeserver_url = 'https://matrix-fsd.epfl.ch'
username = '@user:matrix-fsd.epfl.ch'
password = '1234'

ou_and_persons_list = []
ou_names_to_search = ['isas-fsd', 'isas']

# Token d'accès de l'utilisateur Matrix
access_token = 'syt_dXNlcg_BojZuZNaRrrJPjBiYRMC_18Ofxd'

async def main():

    find_users(ou_names_to_search, ou_and_persons_list)

    # Extraire une personne spécifique de la liste
    user_id_to_ou = get_ous_for_user(ou_and_persons_list, 'nernst')
    print(user_id_to_ou)
    for user_id, (first, second) in user_id_to_ou.items():

        mxid = "@" + user_id + ":matrix-fsd.epfl.ch"
        mymxid = "@nernst:matrix-fsd.epfl.ch"
        mxids = [mxid]
        print(mxids)
        if second[1] == 2:

            space_alias = second[0]
            print (mxid)
            space_id_parent = await create_space(homeserver_url, access_token, space_alias, mxids)
            # await join_users_to_room(homeserver_url, access_token, space_id_parent, mymxid)

            room_alias = second[0]
            room_id_parent = await create_room(homeserver_url, access_token, room_alias, mxids)
            # await join_users_to_room(homeserver_url, access_token, room_id_parent, mymxid)

            await add_room_to_space(homeserver_url, access_token, space_id_parent, room_id_parent)

        if first[1] == 3:
            space_alias = first[0]
            space_id_enfant = await create_space(homeserver_url, access_token, space_alias, mxids)
            # await join_users_to_room(homeserver_url, access_token, space_id_enfant, mymxid)

            room_alias = first[0]
            room_id_enfant = await create_room(homeserver_url, access_token, room_alias, mxids)
            # await join_users_to_room(homeserver_url, access_token, room_id_enfant, mymxid)

            await add_room_to_space(homeserver_url, access_token, space_id_enfant, room_id_enfant)
            await add_room_to_space(homeserver_url, access_token, space_id_parent, space_id_enfant)

def find_users(ou_names_to_search, ou_and_persons_list):
    # Connexion au serveur LDAP
    server = Server(ldap_server)
    conn = Connection(server)

    if not conn.bind():
        print("Échec de la connexion au serveur LDAP")
        return

    for ou_name in ou_names_to_search:
        # Recherche de l'OU spécifiée
        ou_search_base = base_dn
        search_filter = f'(&(objectClass=organizationalUnit)(ou={ou_name}))'  # Filtre pour l'OU spécifique
        conn.search(search_base=ou_search_base, search_filter=search_filter, search_scope=SUBTREE)

        if conn.entries:
            ou_dn = conn.entries[0].entry_dn  # Obtenez le DN de l'OU

            # Comptez le nombre d'occurrences de 'ou=' dans le DN pour déterminer le niveau
            ou_level = ou_dn.count('ou=')

            # Recherche des personnes dans l'OU
            search_filter = '(objectClass=person)'  # Filtre pour les personnes
            conn.search(search_base=ou_dn, search_filter=search_filter, search_scope=SUBTREE, attributes=["uid"])

            persons_in_ou = []
            for person_entry in conn.entries:
                uid = person_entry.uid[0]
                persons_in_ou.append(uid)

            # Ajoutez les noms des personnes et le niveau de l'OU à la liste
            ou_and_persons_list.append((ou_name, ou_level, persons_in_ou))
            

    conn.unbind()

def get_ous_for_user(ou_and_persons_list, user_id):
    user_ous = {}
    for ou_info in ou_and_persons_list:
        ou_name, ou_level, persons_in_ou = ou_info
        if user_id in user_ous:
            user_ous[user_id].append((ou_name, ou_level))
        else:
            user_ous[user_id] = [(ou_name, ou_level)]
    return user_ous

async def create_space(homeserver_url, access_token, alias, users):
    alias = alias + "_space"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    data = {
        'name': alias,
        'room_alias_name': alias,
        'preset': 'public_chat',
        'creation_content': {'type': 'm.space'},
        'invite': users
    }

    response = requests.post(f'{homeserver_url}/_matrix/client/r0/createRoom', headers=headers, json=data)

    if response.status_code == 200:
        response_data = response.json()
        return response_data.get('room_id')
    else:
        raise Exception(f"Failed to create space: {response.text}")

async def create_room(homeserver_url, access_token, alias, users):

    alias = alias + "_room"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    data = {
        'name': alias,
        'room_alias_name': alias,
        'visibility': 'public',
        'preset': 'public_chat',
        'invite': users
    }

    response = requests.post(f'{homeserver_url}/_matrix/client/r0/createRoom', headers=headers, json=data)

    if response.status_code == 200:
        response_data = response.json()
        return response_data.get('room_id')
    else:
        raise Exception(f"Failed to create room: {response.text}")

async def add_room_to_space(homeserver_url, access_token, space_id, room_id):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    data = {
        'via': [homeserver_url]
    }

    response = requests.put(f'{homeserver_url}/_matrix/client/r0/rooms/{space_id}/state/m.space.child/{room_id}', headers=headers, json=data)

    if response.status_code == 200:
        return True
    else:
        raise Exception(f"Failed to add room to space: {response.text}")
    
async def join_users_to_room(homeserver_url, access_token, room_id_or_alias, user_id):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    data = {
            'user_id': user_id
        }

    endpoint_url = f'{homeserver_url}/_matrix/client/v3/join/{room_id_or_alias}'

    response = requests.post(endpoint_url, headers=headers, json=data)

    if response.status_code == 200:
        print(f"Successfully joined user {user_id} to the room {room_id_or_alias}")
    else:
        print(f"Failed to join user {user_id} to the room {room_id_or_alias}. Status code: {response.status_code}. Error: {response.text}")



if __name__ == "__main__":
    asyncio.run(main())


