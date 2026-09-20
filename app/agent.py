# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import urllib.parse
import urllib.request
import uuid
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.models.llm_response import LlmResponse
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import storage
from google.genai import types

from .a2ui_utils import a2ui_callback

# Constants
FIRESTORE_PROJECT = "qwiklabs-gcp-02-16632a3e3848"
RAG_CORPUS_NAME = "projects/646007074919/locations/us-central1/ragCorpora/1355539507373408256"
GCS_BUCKET_NAME = "smart-recipe-assets-qwiklabs-gcp-02-16632a3e3848"
AGENT_ENGINE_ID = "projects/646007074919/locations/us-east1/reasoningEngines/7460223777855504384"


def generate_dish_image(prompt: str, tool_context: ToolContext = None) -> str:
    """Generates an image for a recipe, dish, or ingredient using gemini-3.1-flash-lite-image in the global location.

    Args:
        prompt: Detailed description of the food dish or recipe image to generate.
        tool_context: Optional framework ToolContext injected by ADK.

    Returns:
        The public HTTPS URL of the generated image in Cloud Storage.
    """
    client = genai.Client(
        vertexai=True, project=FIRESTORE_PROJECT, location="global"
    )
    res = client.models.generate_content(
        model="gemini-3.1-flash-lite-image", contents=prompt
    )

    image_bytes = None
    for candidate in res.candidates:
        for part in candidate.content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                image_bytes = part.inline_data.data
                break
        if image_bytes:
            break

    if not image_bytes:
        return "Error: Failed to generate image bytes from model response."

    filename = f"image_{uuid.uuid4().hex[:8]}.jpg"

    # 1. Save artifact if tool_context available
    if tool_context and hasattr(tool_context, "save_artifact"):
        try:
            tool_context.save_artifact(
                filename, image_bytes, mime_type="image/jpeg"
            )
        except Exception as e:
            print(f"Artifact save warning: {e}")

    # 2. Upload to Cloud Storage bucket
    gcs_client = storage.Client(project=FIRESTORE_PROJECT)
    bucket = gcs_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(f"images/{filename}")
    blob.upload_from_string(image_bytes, content_type="image/jpeg")

    public_url = (
        f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/images/{filename}"
    )
    return public_url


def consult_herbal_guide(query: str) -> str:
    """Searches the historical herbal & medical reference guide for remedies, plant uses, and natural health facts.

    Args:
        query: What to look up (e.g. 'cough remedy', 'peppermint', 'headache', 'throat roughness', 'fever').

    Returns:
        The top matching passages from the historical medical guide, or a note if none were found.
    """
    import vertexai
    from vertexai.preview import rag

    vertexai.init(project=FIRESTORE_PROJECT, location="us-central1")
    try:
        resp = rag.retrieval_query(
            text=query,
            rag_resources=[rag.RagResource(rag_corpus=RAG_CORPUS_NAME)],
            rag_retrieval_config=rag.RagRetrievalConfig(top_k=5),
        )
    except Exception as e:
        return f"Herbal guide retrieval failed: {e}"

    contexts = getattr(resp.contexts, "contexts", [])
    passages = [c.text.strip() for c in contexts if getattr(c, "text", "").strip()]
    if not passages:
        return f"No relevant passages found in the herbal guide for query: '{query}'."
    return "\n\n---\n\n".join(passages)


def search_recipes(query: str = "") -> str:
    """Searches the local recipe database in Firestore by keyword, ingredient, or dietary restriction.

    Args:
        query: Optional search term such as an ingredient ('chicken', 'spinach'), a dietary tag ('gluten-free', 'vegan'), or a dish name.

    Returns:
        A formatted list of matching recipes from the database.
    """
    from google.cloud import firestore

    db = firestore.Client(project=FIRESTORE_PROJECT)
    docs = db.collection("recipes").stream()

    results = []
    q = query.lower().strip()
    for doc in docs:
        data = doc.to_dict()
        title = data.get("title", "")
        ingredients = [str(i).lower() for i in data.get("ingredients", [])]
        dietary_tags = [str(t).lower() for t in data.get("dietary_tags", [])]
        instructions = str(data.get("instructions", ""))

        if not q or (
            q in title.lower()
            or any(q in ing for ing in ingredients)
            or any(q in tag for tag in dietary_tags)
            or q in instructions.lower()
        ):
            results.append(data)

    if not results:
        return f"No recipes found in the local database matching query: '{query}'."

    output = []
    for r in results:
        output.append(
            f"• Title: {r.get('title')}\n"
            f"  Prep Time: {r.get('prep_time_minutes')} mins\n"
            f"  Dietary Tags: {', '.join(r.get('dietary_tags', []))}\n"
            f"  Ingredients: {', '.join(r.get('ingredients', []))}\n"
            f"  Instructions: {r.get('instructions')}"
        )
    return "\n\n".join(output)


def add_recipe(
    title: str,
    ingredients: list[str],
    instructions: str,
    prep_time_minutes: int,
    dietary_tags: list[str],
) -> str:
    """Adds a new custom recipe to the Firestore database.

    Args:
        title: The title of the recipe.
        ingredients: List of ingredients required.
        instructions: Preparation and cooking instructions.
        prep_time_minutes: Preparation/cooking time in minutes.
        dietary_tags: List of dietary tags (e.g. 'gluten-free', 'vegan', 'high-protein').

    Returns:
        Confirmation message with the document ID.
    """
    from google.cloud import firestore

    db = firestore.Client(project=FIRESTORE_PROJECT)
    doc_id = title.lower().replace(" ", "-").replace("&", "and")
    doc_ref = db.collection("recipes").document(doc_id)

    recipe_data = {
        "id": doc_id,
        "title": title,
        "ingredients": ingredients,
        "instructions": instructions,
        "prep_time_minutes": prep_time_minutes,
        "dietary_tags": dietary_tags,
    }
    doc_ref.set(recipe_data)
    return f"Successfully added recipe '{title}' to Firestore database with ID '{doc_id}'."


def manage_pantry(action: str, ingredient: str = "", quantity: str = "") -> str:
    """Manages the user's digital household pantry inventory in Firestore.

    Args:
        action: The operation to perform. Must be 'add', 'remove', or 'list'.
        ingredient: The name of the ingredient (required for 'add' and 'remove').
        quantity: Optional amount or quantity description (e.g. '2 lbs', '1 carton', '5 cloves').

    Returns:
        A string summary of the pantry state or action result.
    """
    from google.cloud import firestore

    db = firestore.Client(project=FIRESTORE_PROJECT)
    pantry_ref = db.collection("pantry")

    action_clean = action.lower().strip()

    if action_clean == "list":
        docs = list(pantry_ref.stream())
        if not docs:
            return "Your digital pantry is currently empty."
        items = []
        for doc in docs:
            d = doc.to_dict()
            qty = f" ({d.get('quantity')})" if d.get("quantity") else ""
            items.append(f"• {d.get('ingredient')}{qty}")
        return "Current Pantry Inventory:\n" + "\n".join(items)

    if action_clean == "add":
        if not ingredient:
            return "Error: Please specify an ingredient to add."
        doc_id = ingredient.lower().strip().replace(" ", "-")
        pantry_ref.document(doc_id).set({
            "ingredient": ingredient.strip(),
            "quantity": quantity.strip(),
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        qty_str = f" ({quantity})" if quantity else ""
        return f"Successfully added '{ingredient}'{qty_str} to your digital pantry."

    if action_clean == "remove":
        if not ingredient:
            return "Error: Please specify an ingredient to remove."
        doc_id = ingredient.lower().strip().replace(" ", "-")
        pantry_ref.document(doc_id).delete()
        return f"Successfully removed '{ingredient}' from your digital pantry."

    return f"Error: Unknown action '{action}'. Supported actions are 'add', 'remove', and 'list'."


def search_online_recipes(query: str) -> str:
    """Calls the free public TheMealDB API to search live recipes from around the world.

    Args:
        query: Search term for dish or main ingredient (e.g., 'chicken', 'arrabiata', 'pasta', 'curry').

    Returns:
        Formatted live recipe details including ingredients, instructions, and image URLs.
    """
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={encoded_query}"

    req = urllib.request.Request(url, headers={"User-Agent": "SmartRecipeConcierge/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return f"Failed to fetch live online recipes: {str(e)}"

    meals = data.get("meals")
    if not meals:
        return f"No live online recipes found for query: '{query}'."

    output = []
    for meal in meals[:3]:  # Top 3 results
        title = meal.get("strMeal")
        category = meal.get("strCategory")
        area = meal.get("strArea")
        instructions = meal.get("strInstructions", "")
        thumb = meal.get("strMealThumb")

        ingredients = []
        for i in range(1, 21):
            ing = meal.get(f"strIngredient{i}")
            measure = meal.get(f"strMeasure{i}")
            if ing and ing.strip():
                meas_str = f" ({measure.strip()})" if measure and measure.strip() else ""
                ingredients.append(f"{ing.strip()}{meas_str}")

        output.append(
            f"• Title: {title}\n"
            f"  Category/Cuisine: {category} ({area})\n"
            f"  Image URL: {thumb}\n"
            f"  Ingredients: {', '.join(ingredients)}\n"
            f"  Instructions:\n{instructions.strip()}"
        )

    return "\n\n".join(output)


def get_random_online_recipe() -> str:
    """Calls the free public TheMealDB API to get a random featured recipe suggestion.

    Returns:
        A random dish recipe with ingredients, instructions, and image URL.
    """
    url = "https://www.themealdb.com/api/json/v1/1/random.php"
    req = urllib.request.Request(url, headers={"User-Agent": "SmartRecipeConcierge/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return f"Failed to fetch random recipe: {str(e)}"

    meals = data.get("meals")
    if not meals:
        return "No random recipe available."

    meal = meals[0]
    title = meal.get("strMeal")
    category = meal.get("strCategory")
    area = meal.get("strArea")
    instructions = meal.get("strInstructions", "")
    thumb = meal.get("strMealThumb")

    ingredients = []
    for i in range(1, 21):
        ing = meal.get(f"strIngredient{i}")
        measure = meal.get(f"strMeasure{i}")
        if ing and ing.strip():
            meas_str = f" ({measure.strip()})" if measure and measure.strip() else ""
            ingredients.append(f"{ing.strip()}{meas_str}")

    return (
        f"🎲 Featured Chef Suggestion:\n"
        f"• Title: {title}\n"
        f"  Cuisine: {area} {category}\n"
        f"  Image URL: {thumb}\n"
        f"  Ingredients: {', '.join(ingredients)}\n"
        f"  Instructions:\n{instructions.strip()}"
    )


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


# Code Executor for Sandbox python execution
code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=AGENT_ENGINE_ID
)

# A2UI System Prompt Generation
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are Smart Recipe Concierge, a helpful AI assistant designed to help home cooks "
        "plan meals, track dietary needs, manage ingredients, find custom recipes, consult herbal remedies, "
        "run python code analysis in a sandbox, and generate dish image visuals."
    ),
    workflow_description=(
        "Analyze the user request and return structured UI (A2UI) when appropriate, "
        "or call available tools (search_recipes, add_recipe, manage_pantry, search_online_recipes, "
        "get_random_online_recipe, consult_herbal_guide, generate_dish_image) to fulfill the turn."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL generate_dish_image returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


async def combined_after_model_callback(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> LlmResponse | None:
    """Combines Memory Bank persistence and A2UI dev UI rendering rewrap."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        print(f"Memory callback notice: {e}")
    return a2ui_callback(callback_context, llm_response)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    tools=[
        PreloadMemoryTool(),
        search_recipes,
        add_recipe,
        manage_pantry,
        search_online_recipes,
        get_random_online_recipe,
        consult_herbal_guide,
        generate_dish_image,
        get_weather,
        get_current_time,
    ],
    code_executor=code_executor,
    after_model_callback=combined_after_model_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
