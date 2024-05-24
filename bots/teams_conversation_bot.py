# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import json

from typing import List
from botbuilder.core import CardFactory, TurnContext, MessageFactory
from botbuilder.core.teams import TeamsActivityHandler, TeamsInfo
from botbuilder.schema import CardAction, HeroCard, Mention, ConversationParameters, Attachment, Activity
from botbuilder.schema.teams import TeamInfo, TeamsChannelAccount
from botbuilder.schema._connector_client_enums import ActionTypes
from azure_openai import configure_openai
from servicenow import configure_servicenow
from typing import List

ADAPTIVECARDTEMPLATE = "resources/UserMentionCardTemplate.json"

class TeamsConversationBot(TeamsActivityHandler):

    user_query = ""

    def __init__(self, app_id: str, app_password: str):
        self._app_id = app_id
        self._app_password = app_password

    
    async def get_additional_var_fromUser(self, turn_context: TurnContext, variable_response, count):
        mandatory_variable_not_added = variable_response["missing_variables"]
        if(count == 0):
            await turn_context.send_activity(Activity(type="message", text = "Missing variables are: "+str(mandatory_variable_not_added)+"/nPlease Enter: "+mandatory_variable_not_added[count]))
        else:
            pass

    
    
    
    async def on_message_activity(self, turn_context: TurnContext):
        TurnContext.remove_recipient_mention(turn_context.activity)
        text = turn_context.activity.text.strip()


        print(TeamsConversationBot.user_query)

        if "SyscatalogID: " in text:
            text=text.replace("SyscatalogID: ", "")
            variable_response = configure_servicenow.get_variable_from_query(user_query=TeamsConversationBot.user_query, sys_id=text)
            print(variable_response)
            missing_variables = variable_response["missing_variables"]
            existing_variables = variable_response["existing_variables"]
            if len(missing_variables) == 0:
                final_result = { 'sysparm_quantity' : '1'}
                final_result['variables'] = existing_variables
                add_cart_response = configure_servicenow.add_to_cat_item(final_result=final_result, sys_id=text)
                cart_id = add_cart_response['result']['cart_id']
                submition_response = configure_servicenow.submit_order(cart_id=cart_id)
                request_id = submition_response["result"]["request_number"]
                await turn_context.send_activity(Activity(type="message", text = request_id))
            else:
                await turn_context.send_activity(Activity(type="message", text = "Hello Missing Variable"))
        
            return
        

        ai_response = configure_openai.openAIFunction(text)
        
        if(ai_response["response_detail"] == "general_ai_response"):
            if not ai_response.get("content", ""):
                await turn_context.send_activity(Activity(type="message", text=ai_response["content"]))
            else:
                await turn_context.send_activity(Activity(type="message", text=ai_response["content"]))
        
        
        if(ai_response["response_detail"] == "similar_catalog_items"):
            TeamsConversationBot.user_query = text
            await self._send_card(turn_context, ai_response)

        return

 

    async def _send_card(self, turn_context: TurnContext, ai_response):
        buttons = []

        for catalog_item in ai_response["result"]:
            buttons.append(CardAction(
                type=ActionTypes.message_back,
                title=catalog_item["content"],
                text="SyscatalogID: "+catalog_item["sys_id"]
            ))
        
        card = HeroCard(
            title="Select Catalog Item", text="Click the buttons.", buttons=buttons
        )

        value = await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )
        print(value)


    async def yes_or_nor_card(self, turn_context: TurnContext, ai_response):
        buttons = []

        for catalog_item in ai_response["result"]:
            buttons.append(CardAction(
                type=ActionTypes.message_back,
                title=catalog_item["content"],
                text="SyscatalogID: "+catalog_item["sys_id"]
            ))
        
        card = HeroCard(
            title="Select Catalog Item", text="Click the buttons.", buttons=buttons
        )

        value = await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )
        print(value)


    




































    async def _send_welcome_card(self, turn_context: TurnContext, buttons):
        buttons.append(
            CardAction(
                type=ActionTypes.message_back,
                title="Update Card",
                text="updatecardaction",
                value={"count": 0},
            )
        )
        card = HeroCard(
            title="Welcome Card", text="Click the buttons.", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

    async def _send_update_card(self, turn_context: TurnContext, buttons):
        data = turn_context.activity.value
        data["count"] += 1
        buttons.append(
            CardAction(
                type=ActionTypes.message_back,
                title="Update Card",
                text="updatecardaction",
                value=data,
            )
        )
        card = HeroCard(
            title="Updated card", text=f"Update count {data['count']}", buttons=buttons
        )

        updated_activity = MessageFactory.attachment(CardFactory.hero_card(card))
        updated_activity.id = turn_context.activity.reply_to_id
        await turn_context.update_activity(updated_activity)

    async def _get_member(self, turn_context: TurnContext):
        TeamsChannelAccount: member = None
        try:
            member = await TeamsInfo.get_member(
                turn_context, turn_context.activity.from_property.id
            )
        except Exception as e:
            if "MemberNotFoundInConversation" in e.args[0]:
                await turn_context.send_activity("Member not found.")
            else:
                raise
        else:
            await turn_context.send_activity(f"You are: {member.name}")

    async def _message_all_members(self, turn_context: TurnContext):
        team_members = await self._get_paged_members(turn_context)

        for member in team_members:
            conversation_reference = TurnContext.get_conversation_reference(
                turn_context.activity
            )

            conversation_parameters = ConversationParameters(
                is_group=False,
                bot=turn_context.activity.recipient,
                members=[member],
                tenant_id=turn_context.activity.conversation.tenant_id,
            )

            async def get_ref(tc1):
                conversation_reference_inner = TurnContext.get_conversation_reference(
                    tc1.activity
                )
                return await tc1.adapter.continue_conversation(
                    conversation_reference_inner, send_message, self._app_id
                )

            async def send_message(tc2: TurnContext):
                return await tc2.send_activity(
                    f"Hello {member.name}. I'm a Teams conversation bot."
                )  # pylint: disable=cell-var-from-loop

            await turn_context.adapter.create_conversation(
                conversation_reference, get_ref, conversation_parameters
            )

        await turn_context.send_activity(
            MessageFactory.text("All messages have been sent")
        )

    async def _get_paged_members(
        self, turn_context: TurnContext
    ) -> List[TeamsChannelAccount]:
        paged_members = []
        continuation_token = None

        while True:
            current_page = await TeamsInfo.get_paged_members(
                turn_context, continuation_token, 100
            )
            continuation_token = current_page.continuation_token
            paged_members.extend(current_page.members)

            if continuation_token is None:
                break

        return paged_members

    async def _delete_card_activity(self, turn_context: TurnContext):
        await turn_context.delete_activity(turn_context.activity.reply_to_id)


    async def on_teams_members_added(  # pylint: disable=unused-argument
        self,
        teams_members_added: [TeamsChannelAccount],
        team_info: TeamInfo,
        turn_context: TurnContext,
    ):
        for member in teams_members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    f"Welcome to the team { member.given_name } { member.surname }. "
                )

    async def _mention_adaptive_card_activity(self, turn_context: TurnContext):
        TeamsChannelAccount: member = None
        try:
            member = await TeamsInfo.get_member(
                turn_context, turn_context.activity.from_property.id
            )
        except Exception as e:
            if "MemberNotFoundInConversation" in e.args[0]:
                await turn_context.send_activity("Member not found.")
                return
            else:
                raise

        card_path = os.path.join(os.getcwd(), ADAPTIVECARDTEMPLATE)
        with open(card_path, "rb") as in_file:
            template_json = json.load(in_file)
        
        for t in template_json["body"]:
            t["text"] = t["text"].replace("${userName}", member.name)        
        for e in template_json["msteams"]["entities"]:
            e["text"] = e["text"].replace("${userName}", member.name)
            e["mentioned"]["id"] = e["mentioned"]["id"].replace("${userUPN}", member.user_principal_name)
            e["mentioned"]["id"] = e["mentioned"]["id"].replace("${userAAD}", member.additional_properties["aadObjectId"])
            e["mentioned"]["name"] = e["mentioned"]["name"].replace("${userName}", member.name)
        
        adaptive_card_attachment = Activity(
            attachments=[CardFactory.adaptive_card(template_json)]
        )
        await turn_context.send_activity(adaptive_card_attachment)

    async def _mention_activity(self, turn_context: TurnContext):
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{turn_context.activity.from_property.name}</at>",
            type="mention",
        )

        reply_activity = MessageFactory.text(f"Hello {mention.text}")
        reply_activity.entities = [Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity)
