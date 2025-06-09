# Customer Service Agent Example

This example demonstrates a simple customer service agent built with Temporal's Agent framework. The agent can greet customers and provide order status information.

## Features

- Simple agent with two functions:
  - `greet`: Greets the customer by name
  - `get_order_status`: Retrieves status information for a given order ID

## Components

- **runner.py**: Defines the agent with its functions and starts the agent runner
- **console.py**: Provides a console interface for interacting with the agent

## Prerequisites

- Python 3.8+
- Temporal server running locally (default: localhost:7233)
- uv package manager (see installation instructions below)

## Setup

1. Install uv if you don't have it already:
   ```bash
   curl -sSf https://install.ultraviolet.rs | sh
   ```
   
   For other installation methods, see the [uv documentation](https://github.com/astral-sh/uv).

2. Make sure your Temporal server is running.

## Running the Example

### Start the Agent Runner

```bash
uv run -m examples.customer_service.runner
```

This will start the agent runner, making the agent available for interactions.

### Use the Console Interface

```bash
uv run -m examples.customer_service.console
```

This will start a console interface where you can interact with the agent directly.

## Example Interactions

- Greeting:
  ```
  > Hello, my name is Alice
  hi Alice, how's your day been?
  ```

- Checking order status:
  ```
  > What's the status of my order #12345?
  Your order #12345 is expected to be delivered Tomorrow.
  ```

## Customization

You can extend this example by:
- Adding more functions to the agent
- Modifying the agent's instructions
- Connecting to a real order database
- Integrating with other communication channels