# ticketleap
Unofficial Ticketleap API

## Create and modify TicketLeap events at scale
TicketLeap is unwieldy, and when dealing with large events it can easily become difficult to make changes.
Adding or updating thousands of tickets by hand just isn't reasonable. TicketLeap exposes an API, but it is readonly and so not very useful. 
This library attempts to stand in for the missing API.

One can very quickly and easily create large numbers of tickets and events. For example,
if one wanted to add a new type of ticket to every date:
```python
from ticketleap import TicketLeap
t = TicketLeap(username="foo", password="bar")
t.add_tickets(
  event_slug="slug",
  dates=t.get_dates("slug").keys(),
  tickets=[{"name": "Front Row Seats", "price": 75.0, "inventory": 1}]
)
```
Taking this further, it is just as easy to add hundreds of tickets:
```python
from ticketleap import TicketLeap
t = TicketLeap(username="foo", password="bar")
t.add_tickets(
  event_slug="slug",
  dates=t.get_dates("slug").keys(),
  tickets=[{"name": f"Row {ii} Seats 1pm-5pm", "price": 75.0, "inventory": 1} for ii in range(1, 101)]
        + [{"name": f"Row {ii} Seats 5:30pm-9:30pm", "price": 85.0, "inventory": 1} for ii in range(1, 101)]
        + [{"name": f"Row {ii} Seats 6:30pm-10pm", "price": 85.0, "inventory": 1} for ii in range(1, 101)]
)
```

To delete every ticket in an event (useful for clearing a cloned event) it takes only 3 lines:
```python
from ticketleap import TicketLeap
t = TicketLeap(username="foo", password="bar")
t.clear_event(event_slug="slug")
```

# Methods
The TicketLeap class exposes the following methods: 
```python
def login(self, username: str, password: str) -> None: ...
def upload_image(self, path_to_image: str) -> Tuple[str, str]: ...

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
        ) -> Dict[str, Tuple[None, str]]: ...
        
@staticmethod
def generate_date_dict_from_datetime(
            index: int,
            start: datetime.datetime,
            end: datetime.datetime
        ) -> Dict[str, Tuple[None, str]]: ...
        
def clone_event(
            self,
            *,
            clone_slug: str,
            title: str,
            slug: str,
            dates: List[List[datetime.datetime]]
        ) -> None: ...
        
def clear_event(self, event_slug: str) -> None: ...
def clear_date(self, event_slug: str, date: Union[str, datetime.datetime]) -> None: ...

def delete_ticket(
            self,
            event_slug: str,
            date: Union[str, datetime.datetime],
            ticket_name: Optional[str] = None,
            ticket_uuid: Optional[str] = None
        ) -> None: ...
        
def get_tickets(
            self,
            event_slug: str,
            date: Union[str, datetime.datetime]
        ) -> Dict[str, str]: ...
        
def get_ticket_uuid(
            self,
            event_slug: str,
            date: Union[str, datetime.datetime],
            ticket_name: str
        ) -> str: ...
        
def get_events(self) -> Dict[str, str]: ...
def get_event_uuid(self, event_slug: str) -> str: ...
@staticmethod
def format_default_slug(slug: str) -> str: ...

def add_tickets(
            self,
            event_slug: str,
            dates: List[Union[str, datetime.datetime]],
            tickets: List[Dict[str, str]],
        ) -> None: ...

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
        ) -> None: ...
        
def get_dates(self, event_slug: str) -> Dict[str, Dict[str, Union[datetime.datetime, str]]]: ...

def get_date_uuid(
            self,
            event_slug: str,
            date: Union[str, datetime.datetime]
        ) -> str: ...
```
Additionally, the helper function `iso_8601()` exists to assist in formatting dates:
```python
def iso_8601(date: str) -> str:
    """
    Convert date given by TicketLeap (e.g. Sep 29, 2019 1:00p.m.-10:00p.m.) into ISO 8601
    format (2019-09-29T13:00)
    """
```


