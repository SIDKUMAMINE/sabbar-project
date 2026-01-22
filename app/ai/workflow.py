"""
Workflow LangGraph pour la qualification des leads.
Définit le graph de conversation avec ses nœuds et transitions.
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from datetime import datetime
import logging
import json

from app.ai.state import (
    ConversationState,
    create_initial_state,
    update_state_with_criteria,
    is_ready_for_property_search,
    is_lead_qualified
)
from app.ai.tools import (
    PropertySearchTool,
    PropertySearchCriteria,
    calculate_qualification_score,
    classify_lead_quality
)
from app.ai.prompts import SYSTEM_PROMPT, LEAD_CREATION_PROMPT
from app.core.config import settings

logger = logging.getLogger(__name__)


class QualificationWorkflow:
    """
    Workflow de qualification des leads avec LangGraph.
    Gère le flux de conversation et l'extraction d'informations.
    """
    
    def __init__(self, supabase_client):
        """
        Initialise le workflow.
        
        Args:
            supabase_client: Client Supabase pour accès base de données
        """
        self.supabase = supabase_client
        self.property_search = PropertySearchTool(supabase_client)
        
        # Initialisation du modèle Claude (Sonnet 3.5)
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",  # ✅ Modèle corrigé
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=0.7,
            max_tokens=1024
        )
        
        # Construction du graph
        self.graph = self._build_graph()
        logger.info("QualificationWorkflow initialisé")
    
    def _build_graph(self) -> StateGraph:
        """
        Construit le graph LangGraph avec tous les nœuds.
        
        Returns:
            Graph compilé prêt à l'exécution
        """
        # Création du graph avec l'état typé
        workflow = StateGraph(ConversationState)
        
        # Ajout des nœuds
        workflow.add_node("process_user_input", self._process_user_input)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("extract_criteria", self._extract_criteria)
        workflow.add_node("search_properties", self._search_properties)
        workflow.add_node("calculate_score", self._calculate_score)
        workflow.add_node("finalize_conversation", self._finalize_conversation)
        
        # Définition du point d'entrée
        workflow.set_entry_point("process_user_input")
        
        # Définition des transitions
        workflow.add_edge("process_user_input", "extract_criteria")
        workflow.add_edge("extract_criteria", "calculate_score")
        
        # Décision : faut-il chercher des propriétés ?
        workflow.add_conditional_edges(
            "calculate_score",
            self._should_search_properties,
            {
                "search": "search_properties",
                "skip": "generate_response"
            }
        )
        
        workflow.add_edge("search_properties", "generate_response")
        
        # Décision : conversation terminée ?
        workflow.add_conditional_edges(
            "generate_response",
            self._should_continue_conversation,
            {
                "continue": END,  # Retourne l'état pour la prochaine itération
                "finalize": "finalize_conversation"
            }
        )
        
        workflow.add_edge("finalize_conversation", END)
        
        # Compilation du graph
        return workflow.compile()
    
    async def _process_user_input(self, state: ConversationState) -> ConversationState:
        """
        Traite le message de l'utilisateur.
        
        Args:
            state: État actuel
            
        Returns:
            État mis à jour
        """
        logger.info(f"Traitement du message utilisateur: {state['current_user_message'][:50]}...")
        
        # Ajout du message à l'historique
        state["messages"].append({
            "role": "user",
            "content": state["current_user_message"],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Incrémenter l'engagement
        state["engagement_level"] = min(state["engagement_level"] + 1, 10)
        
        return state
    
    async def _extract_criteria(self, state: ConversationState) -> ConversationState:
        """
        Extrait les critères et informations du message utilisateur.
        
        Args:
            state: État actuel
            
        Returns:
            État mis à jour avec critères extraits
        """
        logger.info("Extraction des critères...")
        
        try:
            # Utilisation du LLM pour extraire les informations structurées
            extraction_prompt = f"""Analyse ce message et extrais les informations pertinentes :

Message : "{state['current_user_message']}"

Contexte de la conversation :
- Budget actuel : {state['budget_min']}-{state['budget_max']} MAD
- Localisation : {', '.join(state['cities']) if state['cities'] else 'Non définie'}
- Type de bien : {state['property_type'] or 'Non défini'}

Extrais et retourne un JSON avec :
- budget_min (nombre ou null)
- budget_max (nombre ou null)
- cities (array de strings)
- property_type (string ou null)
- transaction_type (vente/location/location_vacances ou null)
- bedrooms (nombre ou null)
- surface_min (nombre ou null)
- amenities (array de strings)
- full_name (string ou null)
- phone (string ou null)
- email (string ou null)
- timeframe (string ou null)

Réponds UNIQUEMENT avec le JSON, rien d'autre.
"""
            
            response = self.llm.invoke([
                {"role": "system", "content": "Tu es un extracteur d'informations. Réponds uniquement en JSON valide."},
                {"role": "user", "content": extraction_prompt}
            ])
            
            # Parse la réponse JSON
            extracted = json.loads(response.content)
            logger.debug(f"Critères extraits: {extracted}")
            
            # Mise à jour de l'état avec les critères extraits
            state = update_state_with_criteria(state, extracted)
            
            # Mise à jour des informations personnelles
            if extracted.get("full_name"):
                state["full_name"] = extracted["full_name"]
            if extracted.get("phone"):
                state["phone"] = extracted["phone"]
            if extracted.get("email"):
                state["email"] = extracted["email"]
            if extracted.get("timeframe"):
                state["timeframe"] = extracted["timeframe"]
                state["timeframe_defined"] = True
            
            # Vérifier si contact complet
            state["contact_info_complete"] = bool(state["full_name"] and state["phone"])
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des critères: {str(e)}")
            # En cas d'erreur, on continue sans extraction
        
        return state
    
    async def _calculate_score(self, state: ConversationState) -> ConversationState:
        """
        Calcule le score de qualification du lead.
        
        Args:
            state: État actuel
            
        Returns:
            État mis à jour avec score
        """
        logger.info("Calcul du score de qualification...")
        
        # Calcul du score
        score = calculate_qualification_score(
            budget_defined=state["budget_defined"],
            location_defined=state["location_defined"],
            property_type_defined=state["property_type_defined"],
            timeframe_defined=state["timeframe_defined"],
            contact_info_complete=state["contact_info_complete"],
            specific_criteria_count=state["specific_criteria_count"],
            engagement_level=state["engagement_level"]
        )
        
        state["qualification_score"] = score
        state["lead_quality"] = classify_lead_quality(score)
        
        logger.info(f"Score: {score}/100 - Qualité: {state['lead_quality']}")
        
        # Décider si on doit créer un lead
        state["should_create_lead"] = is_lead_qualified(state) and state["contact_info_complete"]
        
        return state
    
    def _should_search_properties(self, state: ConversationState) -> str:
        """
        Décide si on doit rechercher des propriétés.
        
        Args:
            state: État actuel
            
        Returns:
            "search" ou "skip"
        """
        # Chercher si :
        # 1. On a les critères minimums
        # 2. On n'a pas encore montré de propriétés OU l'utilisateur en demande
        should_search = (
            is_ready_for_property_search(state) and
            (not state["properties_shown"] or "propriété" in state["current_user_message"].lower() or "bien" in state["current_user_message"].lower())
        )
        
        return "search" if should_search else "skip"
    
    async def _search_properties(self, state: ConversationState) -> ConversationState:
        """
        Recherche des propriétés correspondant aux critères.
        
        Args:
            state: État actuel
            
        Returns:
            État mis à jour avec propriétés trouvées
        """
        logger.info("Recherche de propriétés...")
        
        # Construction des critères de recherche
        criteria = PropertySearchCriteria(
            transaction_type=state["transaction_type"],
            property_type=state["property_type"],
            city=state["cities"][0] if state["cities"] else None,
            neighborhood=state["neighborhoods"][0] if state["neighborhoods"] else None,
            min_price=state["budget_min"],
            max_price=state["budget_max"],
            min_bedrooms=state["bedrooms"],
            min_surface=state["surface_min"]
        )
        
        # Recherche
        properties = await self.property_search.search(criteria, limit=5)
        
        state["matched_properties"] = properties
        state["properties_shown"] = True
        
        logger.info(f"Trouvé {len(properties)} propriétés")
        
        return state
    
    async def _generate_response(self, state: ConversationState) -> ConversationState:
        """
        Génère la réponse de l'assistant.
        
        Args:
            state: État actuel
            
        Returns:
            État mis à jour avec réponse
        """
        logger.info("Génération de la réponse...")
        
        # Préparation du contexte pour le LLM
        context = f"""État actuel de la qualification :
- Score : {state['qualification_score']}/100
- Budget : {'Défini' if state['budget_defined'] else 'Non défini'}
- Localisation : {'Définie' if state['location_defined'] else 'Non définie'}
- Type de bien : {'Défini' if state['property_type_defined'] else 'Non défini'}
- Contact : {'Complet' if state['contact_info_complete'] else 'Incomplet'}

Informations collectées :
- Budget : {state['budget_min']}-{state['budget_max']} MAD
- Villes : {', '.join(state['cities']) if state['cities'] else 'Non spécifiées'}
- Type : {state['property_type'] or 'Non spécifié'}
- Chambres : {state['bedrooms'] or 'Non spécifié'}
"""
        
        # Ajout des propriétés trouvées si applicable
        if state["matched_properties"]:
            properties_text = self.property_search.format_results(state["matched_properties"])
            context += f"\n\nPropriétés trouvées :\n{properties_text}"
        
        # Messages pour le LLM
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": context}
        ]
        
        # Ajout de l'historique récent (5 derniers échanges)
        recent_messages = state["messages"][-10:]
        for msg in recent_messages:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Génération de la réponse
        try:
            response = self.llm.invoke(messages)
            assistant_message = response.content
            
            logger.info(f"Réponse générée: {assistant_message[:50]}...")
            
            # Mise à jour de l'état
            state["assistant_response"] = assistant_message
            state["messages"].append({
                "role": "assistant",
                "content": assistant_message,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de réponse: {str(e)}")
            state["assistant_response"] = "Je suis désolé, j'ai rencontré un problème technique. Pouvez-vous reformuler votre message ?"
        
        return state
    
    def _should_continue_conversation(self, state: ConversationState) -> str:
        """
        Décide si la conversation doit continuer ou se terminer.
        
        Args:
            state: État actuel
            
        Returns:
            "continue" ou "finalize"
        """
        # Terminer si :
        # 1. Lead qualifié ET contact complet
        # 2. OU utilisateur dit explicitement qu'il a fini
        
        user_wants_to_end = any(word in state["current_user_message"].lower() for word in [
            "merci", "au revoir", "bye", "stop", "terminé", "fini", "ça suffit"
        ])
        
        should_finalize = (
            (state["should_create_lead"] and state["contact_info_complete"]) or
            user_wants_to_end
        )
        
        return "finalize" if should_finalize else "continue"
    
    async def _finalize_conversation(self, state: ConversationState) -> ConversationState:
        """
        Finalise la conversation et génère un résumé.
        
        Args:
            state: État actuel
            
        Returns:
            État finalisé
        """
        logger.info("Finalisation de la conversation...")
        
        # Génération du résumé
        summary_prompt = f"""Résume cette conversation de qualification immobilière :

{json.dumps(state['messages'][-20:], ensure_ascii=False, indent=2)}

Critères identifiés :
- Budget : {state['budget_min']}-{state['budget_max']} MAD
- Localisation : {', '.join(state['cities'])}
- Type : {state['property_type']}
- Score : {state['qualification_score']}/100
- Qualité : {state['lead_quality']}

Fais un résumé en 3-4 phrases.
"""
        
        try:
            response = self.llm.invoke([
                {"role": "system", "content": "Tu résumes des conversations immobilières de manière concise et professionnelle."},
                {"role": "user", "content": summary_prompt}
            ])
            
            state["conversation_summary"] = response.content
            logger.info("Résumé généré")
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du résumé: {str(e)}")
            state["conversation_summary"] = f"Conversation de qualification - Score: {state['qualification_score']}/100"
        
        state["conversation_complete"] = True
        
        return state
    
    async def run(self, user_message: str, existing_state: ConversationState = None) -> ConversationState:
        """
        Exécute le workflow pour un message utilisateur.
        
        Args:
            user_message: Message de l'utilisateur
            existing_state: État existant (None pour nouvelle conversation)
            
        Returns:
            État mis à jour après traitement
        """
        # Initialisation ou réutilisation de l'état
        if existing_state is None:
            state = create_initial_state()
        else:
            state = existing_state
        
        # Ajout du message utilisateur à l'état
        state["current_user_message"] = user_message
        
        # Exécution du graph
        logger.info(f"Exécution du workflow pour message: {user_message[:50]}...")
        result = await self.graph.ainvoke(state)
        
        logger.info("Workflow terminé")
        return result