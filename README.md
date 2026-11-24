# FastAPI + ARQ + Redis + LangGraph + PostgreSQL

Petit projet local de démonstration :
- FastAPI reçoit les messages.
- ARQ place les tâches dans Redis.
- Un Worker indépendant exécute le graphe LangGraph.
- `AsyncPostgresSaver` conserve l'état et l'historique des conversations dans PostgreSQL.
- Aucun appel LLM : le graphe répond `Bien reçu : ...`.

## Prérequis

- Docker Engine/Desktop et Docker Compose v2.
- Une connexion Internet au premier build de l'image Python si les dépendances ne sont pas déjà en cache.

Les services Redis et PostgreSQL utilisent `pull_policy: never` : Compose ne tentera pas de télécharger ces images.

## Démarrer

À la racine du projet :

```bash
docker compose -f compose.yaml up --build
```

L'API attend que PostgreSQL et Redis soient healthy. Elle initialise ensuite les tables du checkpointer. Le Worker démarre après que l'API soit healthy.

API : http://localhost:8000  
Swagger : http://localhost:8000/docs

## Envoyer un message

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Bonjour"}'
```

Exemple de réponse immédiate :

```json
{
  "job_id": "identifiant-arq",
  "conversation_id": "uuid-de-conversation",
  "status": "queued"
}
```

Le traitement est asynchrone. Conserve les deux identifiants.

## Vérifier le job

```bash
curl http://localhost:8000/jobs/IDENTIFIANT_ARQ
```

Tant que le Worker n'a pas terminé, le statut peut être `queued` ou `in_progress`. Une fois terminé, le résultat contient la réponse fictive.

## Continuer une conversation

Réutilise le `conversation_id` reçu précédemment :

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message":"Et comment fonctionne Redis ?",
    "conversation_id":"UUID_DE_LA_PREMIERE_REQUETE"
  }'
```

Chaque conversation correspond à un `thread_id` LangGraph. Le checkpointer PostgreSQL conserve les messages et les checkpoints du graphe.

## Lire l'historique

```bash
curl http://localhost:8000/conversations/UUID_DE_LA_CONVERSATION
```

## Commandes Docker utiles

```bash
# Logs de tous les services
docker compose -f compose.yaml logs -f

# Logs du Worker seulement
docker compose -f compose.yaml logs -f worker

# Arrêter les containers sans supprimer les données
docker compose -f compose.yaml down

# Arrêter ET supprimer les volumes (efface les données locales)
docker compose -f compose.yaml down -v

# Voir les volumes créés
docker volume ls
```

Les volumes sont nommés avec le préfixe `langgraph_arq_demo_` :
- `langgraph_arq_demo_postgres_data`
- `langgraph_arq_demo_redis_data`

## Lancer sans Docker (optionnel)

Si tu lances FastAPI et ARQ directement sur ta machine, modifie dans `.env` :
- `REDIS_HOST=localhost`
- `DATABASE_URL=postgresql://chatbot:local_dev_password@localhost:5432/chatbot`

Puis installe les dépendances :

```bash
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Dans un deuxième terminal :

```bash
arq app.worker.WorkerSettings
```

Il faut que Redis et PostgreSQL soient démarrés et accessibles sur les ports locaux.

## Notes importantes

- Le mot de passe du `.env.example` est réservé au développement local. Ne pas le réutiliser en production.
- Les noms `redis` et `postgres` sont des hostnames Docker Compose. Depuis un processus lancé directement sur l'hôte, utilise `localhost`.
- `AsyncPostgresSaver.setup()` est exécuté au démarrage de l'API pour créer/mettre à jour les tables de checkpoint avant que le Worker ne démarre.
- Le checkpointer conserve les états/checkpoints LangGraph, pas une table métier de chat conçue sur mesure. Pour un produit, ajoute éventuellement tes propres tables `conversations` et `messages` (utilisateurs, titres, droits d'accès, métadonnées, rétention).
- Pour éviter des écritures concurrentes sur le même thread, le client de démonstration doit attendre la fin d'un job avant d'envoyer le message suivant dans la même conversation. Une application plus avancée doit sérialiser les jobs par conversation.
- Le résultat ARQ est temporaire (ici 1 heure). L'historique durable de la conversation est dans PostgreSQL.
