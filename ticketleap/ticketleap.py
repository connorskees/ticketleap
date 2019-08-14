#!/usr/bin/env python
"""
Create and modify TicketLeap events at scale
"""
import datetime
import json
import logging
import os
import os.path
import re
import string
import time
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import quote

from bs4 import BeautifulSoup
import requests


log = logging.getLogger(__name__)

__all__ = ["TicketLeap", "LoginError"]

IS_WINDOWS = os.name == 'nt'


class LoginError(Exception):
    """Failed to login"""


# https://github.com/PyCQA/pylint/issues/1788#issuecomment-410381475
# pylint: disable=W1203


class TicketLeap:
    """Base TicketLeap request-making class"""
    def __init__(self) -> None:
        __slots__ = ("base_sub_url", "csrf_token", "session")
        self.base_sub_url: str  # base subdomain request url (https://xxx.ticketleap.com)
        self.csrf_token: str
        self.session = requests.Session()
        self.session.headers.update({
            "Host": "www.ticketleap.com",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0)"
                " Gecko/20100101 Firefox/66.0"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Referer": "https://www.google.com/",
            "Connection": "close",
            "Upgrade-Insecure-Requests": "1",
        })

    def login(self, username: str, password: str) -> None:
        """
        Login to TicketLeap

        Args:
            username (str): TicketLeap username
            password (str): TicketLeap password

        Returns:
            None
        """
        base_url = "https://ticketleap.com"
        login_headers = self.session.headers.copy()
        login_headers.update({
            "Referer": "https://www.ticketleap.com/login/",
            "Content-Length": str(72+len(quote(username))+len(quote(password))),
            "Content-Type": "application/x-www-form-urlencoded",
        })

        self.session.get(
            f"{base_url}/login/",
        )

        self.csrf_token = self.session.cookies["csrftoken"]

        login_data = {
            "csrfmiddlewaretoken": self.csrf_token,
            "username": username,
            "password": password
        }

        login_response = self.session.post(
            f"{base_url}/login/",
            headers=login_headers,
            data=login_data
        )

        # Reponse is always 200 even with wrong password
        if login_response.url == "https://ticketleap.com/login/":
            # don't want to log username/password
            log.fatal("Failed to login")
            raise LoginError("Failed to login")

        log.info("Successfully logged in")

        self.base_sub_url = re.sub(r"/admin/$", "", login_response.url)
        host = re.sub(r"^https?://", "", self.base_sub_url)

        log.debug(f"base_sub_url: {self.base_sub_url}")
        log.debug(f"host: {host}")

        self.session.headers.update({
            "Host": host,
            "X-CSRFToken": self.csrf_token
        })

    def upload_image(self, path_to_image: str) -> Tuple[str, str]:
        """
        Upload an event image to TicketLeap

        Args:
            path_to_file (str): Path to image file

        Returns:
            Tuple of
            hero_small_image_url (str): URL formatted as
            https://ticketleap-media-master.s3.amazonaws.com/uuid/full.jpg
            hero_image_url (str): URL formatted as
            https://ticketleap-media-master.s3.amazonaws.com/uuid/hero.jpg
        """
        image_file_types = (
            ".png", ".jpg", ".jpeg", ".tiff", ".gif"
        )
        upload_image_headers = self.session.headers.copy()
        upload_image_headers.update({
            "Accept": "*/*",
            "Referer": f"{self.base_sub_url}/admin/events/create",
            "X-Requested-With": "XMLHttpRequest",
        })

        if not path_to_image.lower().endswith(image_file_types):
            log.fatal(f"Invalid file type:{path_to_image}")
            raise ValueError(f"{path_to_image} is not a valid image file type")

        base_name = os.path.basename(path_to_image)
        _, file_extension = os.path.splitext(path_to_image)
        file_type = f"image/{file_extension.replace('.', '')}"

        with open(path_to_image, mode="rb") as image:
            image_data = {"image_file": (base_name, image, file_type)}
            image_response = self.session.post(
                f"{self.base_sub_url}/admin/galleries/media/create",
                headers=upload_image_headers,
                files=image_data,
            )
            medium = json.loads(image_response.text)["medium"]
            hero_small_image_url = medium["full_url"]
            hero_image_url = medium["hero_url"]

            return hero_small_image_url, hero_image_url

    @staticmethod
    def generate_ticket_dict(
            index: int,
            name: str,
            price: Union[float, str],
            pricing_type: str = "fixed",
            inventory: Union[int, str] = "",
            min_price: Union[int, str] = "",
            visibility: str = "all",
            description: str = "",
            min_per_order: Union[int, str] = "",
            max_per_order: Union[int, str] = "",
            delivery_method: str = "ticket"
        ) -> Dict[str, Tuple[None, str]]:
        """
        Generate ticket dictionary for use in other functions

        Args:
            index (int): Ticket index in list of ticket types
            name (str): Ticket name
            inventory (int, str): Amount of tickets remaining
            pricing_type (str): Type of pricing ('fixed',)
            price (float): Ticket price
            description (str): Ticket description
            min_price (int, str): Minimum ticket price
            visibility (str): Who can see the ticket ('all',)
            min_per_order (int, str): Minimum amount of tickets in one purchase
            max_per_order (int, str): Maximum amount of tickets in one purchase
            delivery_method (str):
        """
        return {
            f"tickets-{index}-name": (None, name),
            f"tickets-{index}-inventory": (None, str(inventory)),
            f"tickets-{index}-limit_inventory": (None, "on" if inventory else ""),
            f"tickets-{index}-pricing_type": (None, pricing_type),
            f"tickets-{index}-price": (None, str(price)),
            f"tickets-{index}-min_price": (None, str(min_price)),
            f"tickets-{index}-visibility": (None, visibility),
            f"tickets-{index}-description": (None, description),
            f"tickets-{index}-sales_start_days_before": (None, ""),
            f"tickets-{index}-sales_start_hours_before": (None, ""),
            f"tickets-{index}-sales_end_days_before": (None, ""),
            f"tickets-{index}-sales_end_hours_before": (None, ""),
            f"tickets-{index}-min_per_order": (None, str(min_per_order)),
            f"tickets-{index}-max_per_order": (None, str(max_per_order)),
            f"tickets-{index}-grouping_key": (None, ""),
            f"tickets-{index}-delivery_method": (None, delivery_method),
        }

    @staticmethod
    def generate_date_dict_from_datetime(
            index: int,
            start: datetime.datetime,
            end: datetime.datetime
        ) -> Dict[str, Tuple[None, str]]:
        """
        Generate event date from two datetime objects

        Args:
            index (int): Index of event date in list (starts at 0)
            start (datetime.datetime): Start of event date
            end (datetime.datetime): End of event date

        Returns:
            dict[str, str] Dictionary of event date info
        """
        start_date = start.strftime("%m/%d/%Y")
        start_time = start.strftime("%I:%M")
        start_ampm = start.strftime("%p").lower()

        end_date = end.strftime("%m/%d/%Y")
        end_time = end.strftime("%I:%M")
        end_ampm = end.strftime("%p").lower()

        return {
            f"dates-{index}-start_date": (None, start_date),
            f"dates-{index}-start_time": (None, start_time),
            f"dates-{index}-start_ampm": (None, start_ampm),
            f"dates-{index}-end_date": (None, end_date),
            f"dates-{index}-end_time": (None, end_time),
            f"dates-{index}-end_ampm": (None, end_ampm),
        }

    def create_event(
            self,
            *,
            title: str,
            description: str,
            image_path: str,
            # hero_image_url: str,
            # hero_small_image_url: str,
            accent_color: str,
            name: str,
            street_address: str,
            city: str,
            region: str,  # state abbreviation
            postal_code: Union[str, int],
            slug: str = "",
            dates: List[List[datetime.datetime]],
            tickets: List[Dict[str, str]],
            facebook_event_id: str = "",
            facebook_page_id: str = "",
            has_ticketleap_event_page: bool = True,
            gallery_type: str = "no-gallery",
            gallery_name: str = "",
            gallery_media: Dict[str, List[str]] = {"media": []},
            gallery_media_config: str = "",
            hero_image_focal_point: str = "center center",
            latitude: Union[float, str] = "",
            longitude: Union[float, str] = "",
            timezone: str = "",
            country_code: str = "USA",
            number_of_tickets: Union[int, str] = "",
            draft_setting: int = 0,
            submit: str = "start sales now"
        ) -> None:
        """
        Create a TicketLeap event

        Args:
            title (str): Event title
            description (str): Event description
            image_path (str): Local path to main event image
            accent_color (str): 6-length hexadecimal color (e.g. #FF00FF)
            name (str): Location name (whatever you want it to be)
            street_address (str): Location street address
            city (str): Location city
            region (str): Two character state abbreviation (e.g. CT, PA, GA)
            postal_code (str, int): 5 digit location postal/zip code
            slug (str): URL slug
            dates: List[List[datetime.datetime]] List of list of start and end
                   dates+times. Must specify year to minutes.
            tickets: List[Dict[str, str]] List of dictionaries specifying tickets
                     properies. Check `generate_ticket_dict()` for parameters
            facebook_event_id: I'm not sure.
            facebook_page_id: I'm not sure.
            has_ticketleap_event_page (bool): I'm not sure.
            gallery_type (str): I'm not sure.
            gallery_name (str): I'm not sure.
            gallery_media: dict[str, list[str]] I'm not sure.
            gallery_media_config (str): I'm not sure.
            hero_image_focal_point (str): Image focal point. Consists of two
                                          words separated by a space. Words
                                          include 'center', 'left', 'right',
                                          'top', 'bottom' and denote position
                                          on a 3x3 grid.
            latitude (float, str): Location latitude
            longitude (float, str): Location longitude
            timezone (str): Location timezone
            country_code (str): ISO country abbreviation (e.g. 'USA')
            number_of_tickets (str): I'm not sure.
            draft_setting (int): I'm not sure.
            submit (str): I'm not sure.
        """
        hero_small_image_url, hero_image_url = self.upload_image(image_path)
        log.debug(f"Uploaded image: Small-{hero_small_image_url} Normal-{hero_image_url}")
        event_data = {
            "csrfmiddlewaretoken": (None, self.csrf_token),
            "facebook_event_id": (None, facebook_event_id),
            "facebook_page_id": (None, facebook_page_id),
            "has_ticketleap_event_page": (None, str(has_ticketleap_event_page)),
            "title": (None, title),
            "slug": (None, slug or self.format_default_slug(title)),
            "description": (None, description),
            "gallery_type": (None, gallery_type),
            "gallery_name": (None, gallery_name),
            "gallery_media": (None, str(gallery_media)),
            "gallery_media_config": (None, gallery_media_config),
            "media-upload-url": "/admin/galleries/media/create",
            "hero_image_url": (None, hero_image_url),
            "hero_small_image_url": (None, hero_small_image_url),
            "hero_image_focal_point": (None, hero_image_focal_point),
            "accent_color": (None, accent_color),
            "latitude": (None, str(latitude)),
            "longitude": (None, str(longitude)),
            "timezone": (None, timezone),
            "name": (None, name),
            "street_address": (None, street_address),
            "country_code": (None, country_code),
            "city": (None, city),
            "region": (None, region),
            "postal_code": (None, str(postal_code)),
            "dates-TOTAL_FORMS": (None, str(len(dates))),
            "dates-INITIAL_FORMS": (None, "0"),
            "dates-MIN_NUM_FORMS": (None, "0"),
            "dates-MAX_NUM_FORMS": (None, "1000"),
            "tickets-TOTAL_FORMS": (None, str(len(tickets))),
            "tickets-INITIAL_FORMS": (None, "0"),
            "tickets-MIN_NUM_FORMS": (None, "0"),
            "tickets-MAX_NUM_FORMS": (None, "1000"),
            "number_of_tickets": (None, str(number_of_tickets)),
            "draft-setting": (None, str(draft_setting)),
            "submit": (None, submit),
        }

        for index, date in enumerate(dates):
            event_data.update(
                **self.generate_date_dict_from_datetime(index, date[0], date[1])
            )

        for index, ticket in enumerate(tickets):
            event_data.update(
                **self.generate_ticket_dict(index, **ticket)
            )

        event_headers = self.session.headers.copy()
        event_headers.update({
            "Referer": f"{self.base_sub_url}/admin/events/create",
        })

        log.debug(
            requests.Request(
                'POST',
                f"{self.base_sub_url}/admin/events/create",
                files=event_data,
                headers=event_headers
            ).prepare().__dict__
        )

        create_response = self.session.post(
            f"{self.base_sub_url}/admin/events/create",
            headers=event_headers,
            files=event_data
        )

        if not create_response.ok:
            log.fatal(f"Failed to create event:{create_response.__dict__}")

            with open("create_response.html", mode="w") as file:
                file.write(create_response.text)

    def clone_event(
            self,
            *,
            clone_slug: str,
            title: str,
            slug: str,
            dates: List[List[datetime.datetime]]
        ) -> None:
        """
        Clone TicketLeap event (copy everything to new event except dates)

        Args:
            clone_slug (str): URL slug of event being cloned
            title (str): Title of new event
            slug (str): Slug of new event
            dates: List of list of start and end dates+times. Must specify year to minutes.

        Returns:
            None
        """
        clone_data: Dict[str, Union[str, Tuple[None, str]]] = {
            "csrfmiddlewaretoken": self.csrf_token,
            "title": title,
            "slug": slug,
            "dates-TOTAL_FORMS": str(len(dates)),
            "dates-INITIAL_FORMS": "0",
            "dates-MIN_NUM_FORMS": "0",
            "dates-MAX_NUM_FORMS": "1000"
        }

        for index, date in enumerate(dates):
            clone_data.update(
                **self.generate_date_dict_from_datetime(index, date[0], date[1])
            )

        clone_headers = self.session.headers.copy()
        clone_headers.update({
            "Accept": "*/*",
            "Referer": f"{self.base_sub_url}/admin/events/",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest"
        })

        clone_uuid = self.get_event_uuid(clone_slug)

        log.debug(
            requests.Request(
                'POST',
                f"{self.base_sub_url}/admin/events/clone/{clone_uuid}",
                data=clone_data,
                headers=clone_headers
            ).prepare().__dict__
        )

        clone_response = self.session.post(
            f"{self.base_sub_url}/admin/events/clone/{clone_uuid}",
            data=clone_data,
            headers=clone_headers
        )

        if not clone_response.ok:
            log.error(f"Failed to clone:{clone_response.__dict__}")

            with open("clone_response.html", mode="w") as file:
                file.write(clone_response.text)

    def clear_event(self, event_slug: str) -> None:
        """
        Remove all tickets from all dates from an event

        Args:
            event_slug (str): Event slug
        """
        start = time.time()
        dates = self.get_dates(event_slug)
        for _, date in dates.items():
            self.clear_date(event_slug, date["uuid"])
        print(f"Took {time.time()-start} seconds")

    def clear_date(self, event_slug: str, date: Union[str, datetime.datetime]) -> None:
        """
        Delete all tickets for date

        Args:
            event_slug (str): Event slug
            date (str, datetime.datetime): Date or date uuid
        """
        tickets = self.get_tickets(event_slug, date)
        date_uuid = self.get_date_uuid(event_slug, date)
        for _, ticket_uuid in tickets.items():
            self.delete_ticket(event_slug, date=date_uuid, ticket_uuid=ticket_uuid)

    def delete_ticket(
            self,
            event_slug: str,
            date: Union[str, datetime.datetime],
            ticket_name: Optional[str] = None,
            ticket_uuid: Optional[str] = None
        ) -> None:
        """
        Delete a ticket from event on date
        Can choose to delete by either name or uuid

        Args:
            event_slug (str): Event URL slug
            date (str, datetime.datetime): Ticket date. Optionally pass UUID
            ticket_name (str, None): Name of ticket
            ticket_uuid (str, None): UUID of ticket

        Returns:
            None
        """
        if ticket_uuid is None and ticket_name is None:
            raise ValueError(
                "No valid ticket identifier passed. Please provide either a name"
                "or uuid"
            )
        delete_headers = self.session.headers.copy()
        delete_headers.update({
            "Accept": "*/*",
            "Referer": f"{self.base_sub_url}/admin/events/{event_slug}/details",
            "X-Requested-With": "XMLHttpRequest"
        })
        date_uuid = self.get_date_uuid(event_slug, date)
        ticket_uuid = ticket_uuid or self.get_ticket_uuid(event_slug, date, ticket_name)
        self.session.get(
            (f"{self.base_sub_url}/admin/events/{event_slug}/performance/"
             f"{date_uuid}/ticket/{ticket_uuid}/delete/?submit=delete"),
            headers=delete_headers
        )

        log.info(f"Successfully deleted {ticket_name or ticket_uuid} in {event_slug} on {date}")

    def modify_post_purchase_message(self, event_slug: str, post_purchase_message: s) -> None:
        """
        Modify the post purchase message (the email sent to users after purchase)

        Args:
            event_slug (str): Event URL slug
            post_purchase_message (str): Post purchase message

        Returns:
            None
        """
        self.session.post(
            f"{self.base_sub_url}/admin/events/{event_slug}/details/modify-post-purchase-message",
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": f"{self.base_sub_url}/admin/events/{event_slug}/details",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
            },
            data={
                "csrfmiddlewaretoken": self.csrf_token,
                "post_purchase_message": post_purchase_message,
            }
        )

    def get_tickets(
            self,
            event_slug: str,
            date: Union[str, datetime.datetime]
        ) -> Dict[str, str]:
        """
        Get uuid of specific ticket by name

        Args:
            event_slug (str): Event URL slug
            date (str, datetime.datetime): Ticket date

        Returns:
            (dict[str, str]) Dict where
                - keys are ticket names
                - values are respective uuids
        """
        date_uuid = self.get_date_uuid(event_slug, date)
        html = self.session.get(
            f"{self.base_sub_url}/admin/events/{event_slug}/"
            f"performance/{date_uuid}/tickets/?ajax=true"
        ).text
        soup = BeautifulSoup(html, "html.parser")
        uuid_regex = re.compile(r"^ticket-type-([a-z0-9-]{36})$")
        tickets = soup.find_all("tr", attrs={"class": "ticket-type"})
        uuids = (uuid_regex.match(t.attrs["id"]).group(1) for t in tickets)
        titles = (t.td.text.strip(" \n\t") for t in tickets)
        return dict(zip(titles, uuids))

    def get_ticket_uuid(
            self,
            event_slug: str,
            date: Union[str, datetime.datetime],
            ticket_name: str
        ) -> str:
        """
        Get uuid of specific ticket by name

        Args:
            event_slug (str): Event URL slug
            date (str, datetime.datetime): Ticket date
            ticket_name (str): Name of ticket

        Returns:
            (str) UUID of given ticket name
        """
        events_dict = self.get_tickets(event_slug=event_slug, date=date)
        ticket_uuid = events_dict.get(ticket_name)

        if ticket_uuid is None:
            error_message = f"Invalid ticket name for {event_slug} on {date}: `{ticket_name}`"
            log.fatal(error_message)
            raise ValueError(error_message)

        return ticket_uuid

    def get_events(self) -> Dict[str, str]:
        """
        Get a list of events and their uuids

        Args:
            None

        Returns:
            (dict) in form of {"slug": "uuid"}
        """
        html = self.session.get(
            f"{self.base_sub_url}/admin/events",
            headers={"Referer": f"{self.base_sub_url}/admin/"}
        ).text
        soup = BeautifulSoup(html, "html.parser")
        title_regex = re.compile(r"^/admin/events/([^/]+)/details\?d=\w{3}-\d{1,2}-\d{4}_at_\d{4}[AP]M")
        uuid_regex = re.compile(r"^#dialog=/admin/events/clone/([a-z0-9-]{36})$")
        # aliasing `title_regex.match()` as `title()` for line length and clarity
        title = title_regex.match
        event_titles = soup.find_all("a", attrs={"title": "Manage"})
        event_uuids = soup.find_all("a", attrs={"title": "Clone"})
        event_titles = (title(t["href"]).group(1) for t in event_titles if t.get("href") and title(t["href"]))
        event_uuids = (uuid_regex.match(t["href"]).group(1) for t in event_uuids)
        event_dict = dict(zip(event_titles, event_uuids))
        log.info(f"Event UUIDS:{event_dict}")
        return event_dict

    def get_event_uuid(self, event_slug: str) -> str:
        """
        Get UUID of specific event by slug

        Args:
            event_slug (str): Event URL slug

        Return:
            (str) UUID of event
        """
        event_uuid = self.get_events().get(event_slug)
        if event_uuid is None:
            log.fatal(f"Invalid event slug: {event_slug}")
            raise ValueError(f"Invalid event slug: {event_slug}")
        return event_uuid

    @staticmethod
    def format_default_slug(slug: str) -> str:
        """Format default page slug"""
        no_punc = slug.translate(str.maketrans('', '', string.punctuation))
        return no_punc.replace(" ", "-").lower()

    def add_tickets(
            self,
            event_slug: str,
            dates: List[Union[str, datetime.datetime]],
            tickets: List[Dict[str, str]],
        ) -> None:
        """
        Add tickets to an event

        Args:
            event_slug (str): Event URL slug
            dates: Dates to add tickets to
            tickets: Tickets to be added
        """
        date_dict_list = self.get_dates(event_slug)
        fmt = lambda date: date if isinstance(date, str) else date.strftime("%Y-%m-%dT%H:%M")
        exists = lambda date: bool(date_dict_list.get(date))
        if dates is not None:
            dates = [fmt(date) for date in dates if exists(fmt(date))]
            date_uuid_list = [date_dict_list.get(date).get("uuid") for date in dates]
        else:
            raise ValueError("No dates given")
        if not date_uuid_list:
            raise ValueError("No valid dates given")
        date_uuid_list = sorted(set(date_uuid_list), key=date_uuid_list.index)
        ticket_headers = self.session.headers.copy()
        ticket_headers.update({
            "Accept": "*/*",
            "Referer": f"{self.base_sub_url}/admin/events/{event_slug}/details",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        })

        for ticket in (self.generate_ticket_dict(0, **t) for t in tickets):
            ticket_params = {
                "csrfmiddlewaretoken": self.csrf_token,
                "dates": date_uuid_list,
                "name": ticket["tickets-0-name"],
                "description": ticket["tickets-0-description"],
                "pricing_type": ticket["tickets-0-pricing_type"],
                "price": ticket["tickets-0-price"],
                "min_price": ticket["tickets-0-min_price"],
                "sales_start_date": "",
                "sales_start_time": "",
                "sales_start_ampm": "pm",
                "sales_end_date": "",
                "sales_end_time": "",
                "sales_end_ampm": "pm",
                "inventory": ticket["tickets-0-inventory"],
                "limit_inventory": ticket["tickets-0-limit_inventory"],
                "min_per_order": ticket["tickets-0-min_per_order"],
                "max_per_order": ticket["tickets-0-max_per_order"],
                "grouping_key": ticket["tickets-0-grouping_key"],
                "delivery_method": ticket["tickets-0-delivery_method"],
            }

            log.debug(
                requests.Request(
                    'POST',
                    f"{self.base_sub_url}/admin/events/{event_slug}/performance/{date_uuid_list[0]}/ticket/add/",
                    data=ticket_params,
                    headers=ticket_headers
                ).prepare().__dict__
            )

            # it is _NOT_ necessary to iterate over dates (check the "dates"
            # key above). We use the first uuid in the list because it is
            # guaranteed to exist
            add_response = self.session.post(
                f"{self.base_sub_url}/admin/events/{event_slug}/performance/{date_uuid_list[0]}/ticket/add/",
                data=ticket_params,
                headers=ticket_headers
            )
            res_dict = add_response.__dict__
            res_dict.pop("_content")
            log.debug(res_dict)

    def modify_ticket(
            self,
            event_slug: str,
            date: Union[str, datetime.datetime],
            ticket_name: str,
            price: Union[str, float],
            description: str,
            inventory: Optional[int] = None,
            pricing_type: str = "fixed",
            new_name: Optional[str] = None
        ) -> None:
        """
        Modify ticket values

        Args:
            event_slug (str): Event URL slug
            date (str, datetime.datetime): Date as datetime instance or ISO 8601 string datetime
            ticket_name (str): Current name of ticket
            price (str, float): New price of ticket
            description (str): New description of ticket
            inventory (str, int): Integer max amount of tickets. None means unlimited inventory
            pricing_type (str):
            new_name (str): New name of ticket. If `None`, name is unchanged
        """

        date_uuid = self.get_date_uuid(event_slug, date)
        ticket_uuid = self.get_ticket_uuid(event_slug, date_uuid, ticket_name)

        edit_data = {
            "csrfmiddlewaretoken": self.csrf_token,
            "dates": date_uuid,
            "name": new_name or ticket_name,
            "description": description,
            "pricing_type": pricing_type,
            "price": str(price),
            "min_price": "",
            "sales_start_date": "",
            "sales_start_time": "",
            "sales_start_ampm": "pm",
            "sales_end_date": "",
            "sales_end_time": "",
            "sales_end_ampm": "pm",
            "limit_inventory": "" if inventory is None else "on",
            "inventory": "" if inventory is None else str(inventory),
            "min_per_order": "",
            "max_per_order": "",
            "grouping_key": "",
            "delivery_method": "ticket",
        }

        edit_headers = self.session.headers.copy()
        edit_headers.update({
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-CSRFToken": self.csrf_token,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_sub_url}/admin/events/{event_slug}/details"
        })

        self.session.get(
            f"{self.base_sub_url}/admin/events/{event_slug}/performance/{date_uuid}/ticket/{ticket_uuid}/edit/",
            headers=edit_headers
        )

        log.debug(
            requests.Request(
                'POST',
                f"{self.base_sub_url}/admin/events/{event_slug}/performance/{date_uuid}/ticket/{ticket_uuid}/edit/",
                headers=edit_headers,
                data=edit_data
            ).prepare().__dict__
        )

        res = self.session.post(
            f"{self.base_sub_url}/admin/events/{event_slug}/performance/{date_uuid}/ticket/{ticket_uuid}/edit/",
            headers=edit_headers,
            data=edit_data,
        )

        if res.ok:
            log.info(f"Successfully updated {ticket_name or ticket_uuid} in {event_slug} on {date}")
            log.debug(edit_data)

        else:
            with open("modify_ticket.html", mode="w") as file:
                file.write(res.text)
            log.error(res.__dict__)

    def get_dates(self, event_slug: str) -> Dict[str, Dict[str, Union[datetime.datetime, str]]]:
        """
        Get list of dates (start and end) and their uuids

        Args:
            event_slug (str): Event slug

        Returns:
            dict where
                - key is (str) iso 8601 format datetime (e.g. 2019-06-20T14:00:00)
                - value is another dict where
                    - keys are 'start', 'end', and 'uuid'
                    - values of 'start' and 'end' are (datetime.datetime)
                    - value of 'uuid' is (str) uuid
        """
        html = self.session.get(
            f"{self.base_sub_url}/admin/events/{event_slug}/details",
            headers={
                "Referer": f"{self.base_sub_url}/admin/events/{event_slug}/completed-first",
            }
        ).text
        soup = BeautifulSoup(html, "html.parser")
        dropdown = soup.find("div", class_="dropdown hide")
        if dropdown is None:
            log.fatal(f"Invalid event slug: `{event_slug}`")
            raise ValueError(f"Invalid event slug: `{event_slug}`")
        dates = {}
        for li in dropdown.ul.find_all("li"):
            start, end = li.text.strip().upper().replace(".", "").split("-")
            if len(end) < 8:  # date is omitted if on same day as start
                end = f"{start.rstrip('0123456789APM:')}{end}"
            # May 13, 2019 2:00PM
            date_fmt = "%b %d, %Y %I:%M%p" if IS_WINDOWS else "%b %-d, %Y %-I:%M%p"
            start = datetime.datetime.strptime(start, date_fmt)
            end = datetime.datetime.strptime(end, date_fmt)
            dates.update({
                start.strftime("%Y-%m-%dT%H:%M"): {
                    "uuid": li.get("id"),
                    "start": start,
                    "end": end
                }
            })
        return dates

    def get_date_uuid(
            self,
            event_slug: str,
            date: Union[str, datetime.datetime]
        ) -> str:
        """
        Get UUID from specific date by string or datetime.datetime

        Args:
            event_slug (str): Event slug

        Returns:
            (str) UUID of date
        """
        date = date if isinstance(date, str) else date.strftime("%Y-%m-%dT%H:%M")
        # allow for known uuids to pass through without making request
        uuid_regex = re.compile(r"^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$")
        if uuid_regex.match(date):
            return date

        date_dict = self.get_dates(event_slug=event_slug).get(date)

        if date_dict is None:
            log.fatal(f"Invalid date for {event_slug}: `{date}`")
            raise ValueError(f"Invalid date for {event_slug}: `{date}`")

        return date_dict["uuid"]


def iso_8601(date: str) -> str:
    """
    Convert given date (e.g. Sep 29, 2019 1:00p.m.-10:00p.m.) into ISO 8601
    format, which is used as keys

    Args:
        date (str): Date in format `Sep 29, 2019 1:00p.m.-10:00p.m.`

    Returns:
        (str) Equivalent date in valid ISO 8601 format
    """
    input_fmt = "%b %d, %Y %I:%M%p" if IS_WINDOWS else "%b %-d, %Y %-I:%M%p"
    output_fmt = "%Y-%m-%dT%H:%M"
    date, _ = date.strip().upper().replace(".", "").split("-")
    return datetime.datetime.strptime(date, input_fmt).strftime(output_fmt)
