"""
Agent IA SABBAR de qualification des leads immobiliers.
Utilise Hugging Face Mistral-7B pour des conversations naturelles en français.
"""
from typing import List, Dict, Any, Optional
import os
import logging
import requests
import uuid
from datetime import datetime
from .prompts import SYSTEM_PROMPT, WELCOME_MESSAGE

logger = logging.getLogger(__name__)


class QualificationAgent:
    """
    Agent conversationnel de qualification des leads immobiliers.
    
    Fonctionnalités :
    - Conversations naturelles en français (Mistral-7B)
    - Extraction automatique des critères (budget, ville, type)
    - Calcul du score de qualification (0-100)
    - Matching avec les propriétés disponibles
    - Création automatique des leads qualifiés
    """
    
    def __init__(self, supabase_client):
        """
        Initialise l'agent avec Hugging Face et Supabase.
        
        Args:
            supabase_client: Client Supabase pour la persistance
        """
        # Configuration Hugging Face
        self.api_token = os.getenv("HUGGINGFACE_API_TOKEN")
        if not self.api_token:
            raise ValueError("❌ HUGGINGFACE_API_TOKEN manquante dans .env")
        
        self.model = os.getenv("LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model}"
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        # Client Supabase
        self.supabase = supabase_client
        
        # Cache des conversations actives (pour performance)
        self._conversations_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"✅ QualificationAgent initialisé avec {self.model}")
    
    # ========================================================================
    # MÉTHODES PUBLIQUES (appelées par les endpoints)
    # ========================================================================
    
    async def start_conversation(
        self, 
        initial_message: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Démarre une nouvelle conversation de qualification.
        
        Args:
            initial_message: Message initial de l'utilisateur (optionnel)
            user_id: ID de l'agent immobilier assigné (optionnel)
        
        Returns:
            Dict avec conversation_id, response, status, qualification_score
        """
        # Générer un ID unique
        conversation_id = str(uuid.uuid4())
        
        # Initialiser l'état de la conversation
        conversation_state = {
            "conversation_id": conversation_id,
            "messages": [],
            "criteria": {},
            "contact_info": {"name": None, "phone": None, "email": None},
            "qualification_score": 0,
            "lead_quality": "cold",
            "status": "active",
            "lead_id": None,
            "created_at": datetime.utcnow().isoformat(),
            "user_id": user_id
        }
        
        # Message de bienvenue par défaut
        if not initial_message:
            response_text = WELCOME_MESSAGE
            conversation_state["messages"].append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            # Traiter le message initial
            result = await self._process_message(
                conversation_state=conversation_state,
                user_message=initial_message
            )
            response_text = result["response"]
        
        # Sauvegarder dans le cache
        self._conversations_cache[conversation_id] = conversation_state
        
        # Persister dans Supabase (async via thread pool)
        await self._save_conversation_to_db(conversation_state)
        
        logger.info(f"✅ Conversation {conversation_id} créée")
        
        return {
            "conversation_id": conversation_id,
            "response": response_text,
            "status": "active",
            "qualification_score": conversation_state["qualification_score"]
        }
    
    async def continue_conversation(
        self,
        conversation_id: str,
        user_message: str
    ) -> Dict[str, Any]:
        """
        Continue une conversation existante avec un nouveau message.
        
        Args:
            conversation_id: ID de la conversation
            user_message: Nouveau message de l'utilisateur
        
        Returns:
            Dict avec response, score, lead_quality, matched_properties, etc.
        
        Raises:
            ValueError: Si conversation non trouvée
        """
        # Récupérer la conversation (cache ou DB)
        conversation_state = await self._get_conversation(conversation_id)
        
        if not conversation_state:
            raise ValueError(f"Conversation {conversation_id} non trouvée")
        
        # Traiter le message
        result = await self._process_message(
            conversation_state=conversation_state,
            user_message=user_message
        )
        
        # Sauvegarder les changements
        self._conversations_cache[conversation_id] = conversation_state
        await self._save_conversation_to_db(conversation_state)
        
        # Créer le lead si qualifié
        lead_id = None
        if result["should_create_lead"] and not conversation_state["lead_id"]:
            lead_id = await self._create_lead(conversation_state)
            conversation_state["lead_id"] = lead_id
            await self._save_conversation_to_db(conversation_state)
        
        logger.info(
            f"✅ Message traité - Score: {result['qualification_score']}/100, "
            f"Lead: {result['should_create_lead']}"
        )
        
        return {
            "conversation_id": conversation_id,
            "response": result["response"],
            "qualification_score": result["qualification_score"],
            "lead_quality": result["lead_quality"],
            "should_create_lead": result["should_create_lead"],
            "conversation_complete": result["conversation_complete"],
            "properties_shown": result["properties_shown"],
            "matched_properties_count": result["matched_properties_count"],
            "lead_id": lead_id or conversation_state["lead_id"],
            "criteria_extracted": result["criteria_extracted"]
        }
    
    async def get_conversation_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère l'état complet d'une conversation.
        
        Args:
            conversation_id: ID de la conversation
        
        Returns:
            État complet ou None si non trouvée
        """
        conversation_state = await self._get_conversation(conversation_id)
        
        if not conversation_state:
            return None
        
        return {
            "conversation_id": conversation_id,
            "messages": conversation_state["messages"],
            "qualification_score": conversation_state["qualification_score"],
            "lead_quality": conversation_state["lead_quality"],
            "criteria": conversation_state["criteria"],
            "contact_info": conversation_state["contact_info"],
            "status": conversation_state["status"],
            "lead_id": conversation_state.get("lead_id")
        }
    
    async def end_conversation(
        self,
        conversation_id: str,
        reason: str = "completed"
    ) -> Dict[str, Any]:
        """
        Termine une conversation et génère un résumé.
        
        Args:
            conversation_id: ID de la conversation
            reason: Raison de la fin (completed, abandoned, error)
        
        Returns:
            Résumé de la conversation
        """
        conversation_state = await self._get_conversation(conversation_id)
        
        if not conversation_state:
            return {"error": f"Conversation {conversation_id} non trouvée"}
        
        # Créer le lead si pas encore fait et qualifié
        lead_created = False
        lead_id = conversation_state.get("lead_id")
        
        if not lead_id and conversation_state["qualification_score"] >= 50:
            lead_id = await self._create_lead(conversation_state)
            lead_created = True
        
        # Générer le résumé
        summary = self._generate_summary(conversation_state)
        
        # Marquer comme terminée
        conversation_state["status"] = "completed"
        conversation_state["ended_at"] = datetime.utcnow().isoformat()
        conversation_state["end_reason"] = reason
        
        # Sauvegarder
        await self._save_conversation_to_db(conversation_state)
        
        # Retirer du cache
        if conversation_id in self._conversations_cache:
            del self._conversations_cache[conversation_id]
        
        logger.info(f"✅ Conversation {conversation_id} terminée - Lead créé: {lead_created}")
        
        return {
            "conversation_id": conversation_id,
            "status": "completed",
            "qualification_score": conversation_state["qualification_score"],
            "lead_quality": conversation_state["lead_quality"],
            "lead_created": lead_created,
            "lead_id": lead_id,
            "messages_count": len(conversation_state["messages"]),
            "summary": summary
        }
    
    def get_active_conversations_count(self) -> int:
        """Retourne le nombre de conversations actives en cache."""
        return len(self._conversations_cache)
    
    # ========================================================================
    # MÉTHODES PRIVÉES (logique interne)
    # ========================================================================
    
    async def _process_message(
        self,
        conversation_state: Dict[str, Any],
        user_message: str
    ) -> Dict[str, Any]:
        """
        Traite un message utilisateur et met à jour l'état de la conversation.
        
        Returns:
            Dict avec response, score, lead_quality, etc.
        """
        # Ajouter le message utilisateur
        conversation_state["messages"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Extraire les critères de toute la conversation
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in conversation_state["messages"]
        ])
        
        new_criteria = self._extract_criteria(conversation_text)
        conversation_state["criteria"].update(new_criteria)
        
        # Extraire les informations de contact
        contact_info = self._extract_contact_info(conversation_text)
        conversation_state["contact_info"].update(contact_info)
        
        # Calculer le score
        score = self._calculate_score(
            conversation_state["criteria"],
            conversation_state["contact_info"]
        )
        conversation_state["qualification_score"] = score
        
        # Déterminer la qualité du lead
        lead_quality = self._determine_lead_quality(score)
        conversation_state["lead_quality"] = lead_quality
        
        # Matcher avec les propriétés
        matched_properties = []
        if conversation_state["criteria"]:
            matched_properties = await self._match_properties(conversation_state["criteria"])
        
        # Générer la réponse de l'IA
        response_text = await self._generate_ai_response(
            conversation_state=conversation_state,
            matched_properties=matched_properties
        )
        
        # Ajouter la réponse de l'assistant
        conversation_state["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Déterminer si on doit créer le lead
        should_create_lead = (
            score >= 50 and
            conversation_state["contact_info"]["name"] and
            conversation_state["contact_info"]["phone"]
        )
        
        # Déterminer si la conversation est complète
        conversation_complete = score >= 70 or len(conversation_state["messages"]) > 20
        
        # État d'extraction des critères
        criteria_extracted = {
            "budget": bool(conversation_state["criteria"].get("budget_min") or 
                          conversation_state["criteria"].get("budget_max")),
            "location": bool(conversation_state["criteria"].get("preferred_cities")),
            "property_type": bool(conversation_state["criteria"].get("preferred_types")),
            "contact": bool(conversation_state["contact_info"]["phone"])
        }
        
        return {
            "response": response_text,
            "qualification_score": score,
            "lead_quality": lead_quality,
            "should_create_lead": should_create_lead,
            "conversation_complete": conversation_complete,
            "properties_shown": len(matched_properties) > 0,
            "matched_properties_count": len(matched_properties),
            "criteria_extracted": criteria_extracted
        }
    
    async def _generate_ai_response(
        self,
        conversation_state: Dict[str, Any],
        matched_properties: List[Dict] = None
    ) -> str:
        """Génère la réponse de l'IA avec Hugging Face Mistral."""
        
        # Construire le contexte
        context = self._build_context(conversation_state, matched_properties or [])
        
        # Construire le prompt Mistral
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context}
        ] + conversation_state["messages"]
        
        prompt = self._build_mistral_prompt(messages)
        
        # Appeler Hugging Face
        response_text = await self._call_huggingface(prompt)
        
        return response_text
    
    def _build_context(
        self,
        conversation_state: Dict[str, Any],
        matched_properties: List[Dict]
    ) -> str:
        """Construit le contexte pour l'IA."""
        context = f"""
CONTEXTE DE LA CONVERSATION :
- Score de qualification actuel : {conversation_state['qualification_score']}/100
- Qualité du lead : {conversation_state['lead_quality']}
- Critères extraits : {conversation_state['criteria']}
- Contact : {conversation_state['contact_info']}
"""
        
        if matched_properties:
            context += f"\n\n{len(matched_properties)} PROPRIÉTÉS CORRESPONDANTES TROUVÉES :\n"
            for i, prop in enumerate(matched_properties[:3], 1):  # Max 3 propriétés
                context += f"""
{i}. {prop.get('title', 'Sans titre')} - {prop.get('city', 'Ville inconnue')}
   Prix : {prop.get('price', 0):,.0f} MAD
   Type : {prop.get('property_type', 'Non spécifié')}
   Superficie : {prop.get('area', 0)} m²
   Chambres : {prop.get('bedrooms', 0)}
"""
        
        return context
    
    def _build_mistral_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Construit le prompt au format Mistral Instruct.
        Format: <s>[INST] {system}\n{user} [/INST] {assistant}</s>
        """
        # Séparer le message système
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_messages = [m for m in messages if m["role"] != "system"]
        
        prompt = f"<s>[INST] {system_msg}\n\n"
        
        for i, msg in enumerate(user_messages):
            if msg["role"] == "user":
                if i == len(user_messages) - 1:
                    prompt += f"{msg['content']} [/INST]"
                else:
                    prompt += f"{msg['content']} [/INST] "
            
            elif msg["role"] == "assistant":
                prompt += f"{msg['content']}</s>"
                if i < len(user_messages) - 1:
                    prompt += "<s>[INST] "
        
        return prompt
    
    async def _call_huggingface(self, prompt: str, max_tokens: int = 500) -> str:
        """Appelle l'API Hugging Face Inference."""
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": float(os.getenv("LLM_TEMPERATURE", 0.7)),
                "top_p": 0.95,
                "do_sample": True,
                "return_full_text": False,
                "repetition_penalty": 1.2
            }
        }
        
        try:
            logger.info("📡 Appel Hugging Face API...")
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 503:
                logger.warning("⏳ Modèle en cours de chargement...")
                return "⏳ Le modèle IA est en cours d'initialisation. Veuillez patienter 20-30 secondes et réessayer."
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    generated_text = result[0].get("generated_text", "").strip()
                    logger.info(f"✅ Réponse générée ({len(generated_text)} chars)")
                    return generated_text
            
            elif response.status_code == 401:
                logger.error("❌ Token HF invalide")
                return "Erreur : Token API invalide."
            
            logger.error(f"❌ Erreur API {response.status_code}")
            return "Désolé, une erreur technique est survenue."
        
        except Exception as e:
            logger.error(f"❌ Exception HF: {e}")
            return "Désolé, une erreur technique est survenue."
    
    def _extract_criteria(self, conversation_text: str) -> Dict[str, Any]:
        """Extrait les critères de recherche immobilière."""
        criteria = {}
        text_lower = conversation_text.lower()
        
        # VILLES MAROCAINES
        cities_map = {
            "Casablanca": ["casablanca", "casa"],
            "Rabat": ["rabat"],
            "Marrakech": ["marrakech", "marrakesh"],
            "Fès": ["fès", "fes"],
            "Tanger": ["tanger", "tangier"],
            "Agadir": ["agadir"],
            "Meknès": ["meknès", "meknes"],
            "Oujda": ["oujda"],
            "Tétouan": ["tétouan", "tetouan"],
            "Kénitra": ["kénitra", "kenitra"]
        }
        
        detected_cities = []
        for city, keywords in cities_map.items():
            if any(kw in text_lower for kw in keywords):
                detected_cities.append(city)
        
        if detected_cities:
            criteria["preferred_cities"] = detected_cities
        
        # TYPES DE BIENS
        types_map = {
            "appartement": ["appartement", "appart"],
            "villa": ["villa"],
            "maison": ["maison"],
            "riad": ["riad"],
            "terrain": ["terrain"],
            "bureau": ["bureau"],
            "local_commercial": ["local commercial", "local", "commerce"]
        }
        
        detected_types = []
        for type_key, keywords in types_map.items():
            if any(kw in text_lower for kw in keywords):
                detected_types.append(type_key)
        
        if detected_types:
            criteria["preferred_types"] = detected_types
        
        # TYPE DE TRANSACTION
        if any(w in text_lower for w in ["vente", "acheter", "achat", "achète"]):
            criteria["transaction_type"] = "vente"
        elif any(w in text_lower for w in ["location", "louer", "loue"]):
            criteria["transaction_type"] = "location"
        
        # BUDGET (regex)
        import re
        budget_patterns = [
            r'(\d+)\s*(?:millions?|m\b)',
            r'(\d{1,3}(?:\s?\d{3}){2,})',
            r'(\d{7,})',
        ]
        
        for pattern in budget_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                try:
                    amount_str = matches[0].replace(" ", "").replace("millions", "").replace("m", "")
                    amount = int(amount_str)
                    
                    if "million" in text_lower or re.search(r'\d+\s*m\b', text_lower):
                        amount *= 1_000_000
                    
                    context = text_lower[max(0, text_lower.find(matches[0])-50):text_lower.find(matches[0])+50]
                    
                    if any(w in context for w in ["max", "jusqu'à", "pas plus"]):
                        criteria["budget_max"] = amount
                    elif any(w in context for w in ["min", "au moins", "partir"]):
                        criteria["budget_min"] = amount
                    else:
                        criteria["budget_max"] = amount
                    
                    break
                except:
                    pass
        
        # CHAMBRES
        room_matches = re.findall(r'(\d+)\s*chambres?', text_lower)
        if room_matches:
            criteria["rooms"] = int(room_matches[0])
        
        # SUPERFICIE
        area_matches = re.findall(r'(\d+)\s*m[²2]', text_lower)
        if area_matches:
            criteria["area"] = int(area_matches[0])
        
        return criteria
    
    def _extract_contact_info(self, conversation_text: str) -> Dict[str, Optional[str]]:
        """Extrait les informations de contact."""
        import re
        contact = {"name": None, "phone": None, "email": None}
        
        # Téléphone marocain
        phone_patterns = [
            r'(\+212|0)[5-7]\d{8}',
            r'(\d{10})'
        ]
        for pattern in phone_patterns:
            matches = re.findall(pattern, conversation_text)
            if matches:
                contact["phone"] = matches[0]
                break
        
        # Email
        email_matches = re.findall(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', conversation_text)
        if email_matches:
            contact["email"] = email_matches[0]
        
        # Nom (très basique, cherche "je m'appelle X" ou "mon nom est X")
        name_patterns = [
            r"(?:je m'appelle|mon nom est|je suis)\s+([A-ZÀ-Ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ]+)?)",
        ]
        for pattern in name_patterns:
            matches = re.findall(pattern, conversation_text, re.IGNORECASE)
            if matches:
                contact["name"] = matches[0].strip()
                break
        
        return contact
    
    def _calculate_score(
        self,
        criteria: Dict[str, Any],
        contact_info: Dict[str, Optional[str]]
    ) -> int:
        """Calcule le score de qualification (0-100)."""
        score = 0
        
        # Critères essentiels
        if criteria.get("budget_min") or criteria.get("budget_max"):
            score += 25
        if criteria.get("preferred_cities"):
            score += 20
        if criteria.get("preferred_types"):
            score += 15
        if criteria.get("transaction_type"):
            score += 10
        
        # Critères secondaires
        if criteria.get("rooms"):
            score += 5
        if criteria.get("area"):
            score += 5
        
        # Contact
        if contact_info.get("name"):
            score += 5
        if contact_info.get("phone"):
            score += 10
        if contact_info.get("email"):
            score += 5
        
        return min(score, 100)
    
    def _determine_lead_quality(self, score: int) -> str:
        """Détermine la qualité du lead."""
        if score >= 70:
            return "hot"
        elif score >= 40:
            return "warm"
        else:
            return "cold"
    
    async def _match_properties(self, criteria: Dict[str, Any]) -> List[Dict]:
        """Recherche les propriétés correspondant aux critères."""
        try:
            query = self.supabase.table("properties").select("*")
            
            # Filtres
            if criteria.get("preferred_cities"):
                query = query.in_("city", criteria["preferred_cities"])
            
            if criteria.get("preferred_types"):
                query = query.in_("property_type", criteria["preferred_types"])
            
            if criteria.get("transaction_type"):
                query = query.eq("transaction_type", criteria["transaction_type"])
            
            if criteria.get("budget_max"):
                query = query.lte("price", criteria["budget_max"])
            
            if criteria.get("budget_min"):
                query = query.gte("price", criteria["budget_min"])
            
            if criteria.get("rooms"):
                query = query.gte("bedrooms", criteria["rooms"])
            
            # Limiter à 5 résultats
            result = query.limit(5).execute()
            
            logger.info(f"🔍 {len(result.data)} propriétés trouvées")
            return result.data
        
        except Exception as e:
            logger.error(f"❌ Erreur matching: {e}")
            return []
    
    async def _create_lead(self, conversation_state: Dict[str, Any]) -> Optional[str]:
        """Crée un lead dans Supabase."""
        try:
            lead_data = {
                "name": conversation_state["contact_info"]["name"] or "Prospect",
                "phone": conversation_state["contact_info"]["phone"],
                "email": conversation_state["contact_info"]["email"],
                "preferred_cities": conversation_state["criteria"].get("preferred_cities", []),
                "preferred_types": conversation_state["criteria"].get("preferred_types", []),
                "budget_min": conversation_state["criteria"].get("budget_min"),
                "budget_max": conversation_state["criteria"].get("budget_max"),
                "qualification_score": conversation_state["qualification_score"],
                "source": "chatbot",
                "status": "nouveau"
            }
            
            result = self.supabase.table("leads").insert(lead_data).execute()
            
            lead_id = result.data[0]["id"]
            logger.info(f"✅ Lead {lead_id} créé")
            return lead_id
        
        except Exception as e:
            logger.error(f"❌ Erreur création lead: {e}")
            return None
    
    def _generate_summary(self, conversation_state: Dict[str, Any]) -> str:
        """Génère un résumé de la conversation."""
        criteria = conversation_state["criteria"]
        contact = conversation_state["contact_info"]
        
        summary = f"Prospect "
        
        if contact.get("name"):
            summary += f"{contact['name']} "
        
        summary += f"recherche "
        
        if criteria.get("preferred_types"):
            summary += f"{', '.join(criteria['preferred_types'])} "
        else:
            summary += "un bien "
        
        if criteria.get("preferred_cities"):
            summary += f"à {', '.join(criteria['preferred_cities'])} "
        
        if criteria.get("budget_max"):
            summary += f"budget max {criteria['budget_max']:,.0f} MAD "
        
        summary += f"(Score: {conversation_state['qualification_score']}/100)"
        
        return summary
    
    async def _get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une conversation du cache ou de la DB."""
        # Vérifier le cache d'abord
        if conversation_id in self._conversations_cache:
            return self._conversations_cache[conversation_id]
        
        # Sinon, charger depuis Supabase
        try:
            result = self.supabase.table("conversations").select("*").eq("id", conversation_id).execute()
            
            if result.data:
                conversation_state = result.data[0].get("state", {})
                self._conversations_cache[conversation_id] = conversation_state
                return conversation_state
        
        except Exception as e:
            logger.error(f"❌ Erreur chargement conversation: {e}")
        
        return None
    
    async def _save_conversation_to_db(self, conversation_state: Dict[str, Any]):
        """Sauvegarde une conversation dans Supabase."""
        try:
            conversation_id = conversation_state["conversation_id"]
            
            data = {
                "id": conversation_id,
                "state": conversation_state,
                "qualification_score": conversation_state["qualification_score"],
                "status": conversation_state["status"],
                "lead_id": conversation_state.get("lead_id"),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Upsert (insert ou update)
            self.supabase.table("conversations").upsert(data).execute()
            
            logger.debug(f"💾 Conversation {conversation_id} sauvegardée")
        
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde conversation: {e}")