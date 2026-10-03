# Usability improvements — Campus Customs

Two changes on the website and two on the shop assistant. For each one: what was added, and why it helps a shopper or the business.

## Frontend

### 1. Home page copy

The opening text, the three short sections, and the featured-products heading now talk about the clothes: licensed Yale hoodies, crewnecks, tees, and jackets; fleece and cotton the Broadway shop actually sells; college, graduate-school, and team marks; and finding a size.

A shopper lands on a reason to buy, and the page reads as the store rather than as notes about how the site is built.

### 2. Search on the Products page

A search box filters the catalogue by name, garment type, description, colors, and tags, so a query like "hoodie" or a college name narrows the grid. Product pages list the color names and show size counts for the piece as a whole.

Shoppers can find a college, team, or garment without scrolling the full shelf, and they are not offered a color picker that would imply stock is tracked by color.

## Backend

### 1. Color check

The assistant has a `check_color` tool. Before it says a piece comes in a color, it reads that product's catalogue color list ("navy" matches "navy blue"). If the customer asked about a color and the tool was not used, or the reply disagrees with the list, the reply is not sent.

"Do you have this in pink?" is answered from the colors the shop actually sells, so a customer is not promised a color that is not on the piece.

### 2. Prices and size counts must match the database

A dollar amount in the reply (`$68` or "68 dollars") has to be a price `get_product_info` just returned. A size count ("5 in stock," "only 2," "medium is 0") has to be a quantity `get_stock` just returned.

Shoppers can trust the price and how many are left in their size, and the shop does not quote a number that was never in inventory.
