// =============================================================================
// Neo4j Design Pattern Knowledge Graph - Seed Script
// =============================================================================
// This script initializes a comprehensive design pattern knowledge graph.
// Run with: cypher-shell -f init-patterns.cypher
// =============================================================================

// -----------------------------------------------------------------------------
// 1. CONSTRAINTS
// -----------------------------------------------------------------------------
CREATE CONSTRAINT pattern_name_unique IF NOT EXISTS FOR (p:Pattern) REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT language_name_unique IF NOT EXISTS FOR (l:Language) REQUIRE l.name IS UNIQUE;
CREATE CONSTRAINT category_name_unique IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT principle_name_unique IF NOT EXISTS FOR (pr:Principle) REQUIRE pr.name IS UNIQUE;

// -----------------------------------------------------------------------------
// 2. INDEXES
// -----------------------------------------------------------------------------
CREATE FULLTEXT INDEX pattern_description_fulltext IF NOT EXISTS FOR (p:Pattern) ON EACH [p.description];

// -----------------------------------------------------------------------------
// 3. CATEGORY NODES
// -----------------------------------------------------------------------------
CREATE (:Category {name: 'creational'});
CREATE (:Category {name: 'structural'});
CREATE (:Category {name: 'behavioral'});
CREATE (:Category {name: 'architectural'});
CREATE (:Category {name: 'concurrency'});
CREATE (:Category {name: 'integration'});

// -----------------------------------------------------------------------------
// 4. LANGUAGE NODES
// -----------------------------------------------------------------------------
CREATE (:Language {name: 'python'});
CREATE (:Language {name: 'go'});
CREATE (:Language {name: 'rust'});
CREATE (:Language {name: 'typescript'});
CREATE (:Language {name: 'java'});
CREATE (:Language {name: 'c'});
CREATE (:Language {name: 'cpp'});

// -----------------------------------------------------------------------------
// 5. PRINCIPLE NODES
// -----------------------------------------------------------------------------
CREATE (:Principle {name: 'SRP'});
CREATE (:Principle {name: 'OCP'});
CREATE (:Principle {name: 'LSP'});
CREATE (:Principle {name: 'ISP'});
CREATE (:Principle {name: 'DIP'});
CREATE (:Principle {name: 'DRY'});
CREATE (:Principle {name: 'KISS'});
CREATE (:Principle {name: 'YAGNI'});
CREATE (:Principle {name: 'separation-of-concerns'});
CREATE (:Principle {name: 'composition-over-inheritance'});

// =============================================================================
// 6. CREATIONAL PATTERNS
// =============================================================================

CREATE (p:Pattern {
  name: 'Singleton',
  description: 'Ensures a class has only one instance and provides a global point of access to it. Controls concurrent access to shared resources.',
  intent: 'Ensure exactly one instance of a class exists and provide global access.',
  when_to_use: 'When exactly one object is needed to coordinate actions across the system, such as configuration managers, connection pools, or logging services.',
  when_not_to_use: 'When global state makes testing difficult, when multiple instances may be needed later, or when it hides dependencies.',
  complexity: 'simple',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Factory Method',
  description: 'Defines an interface for creating an object but lets subclasses decide which class to instantiate. Defers instantiation to subclasses.',
  intent: 'Define an interface for object creation, deferring the actual instantiation to subclasses.',
  when_to_use: 'When a class cannot anticipate the type of objects it needs to create, or when subclasses should specify the objects they create.',
  when_not_to_use: 'When the creation logic is trivial and unlikely to change, adding unnecessary abstraction layers.',
  complexity: 'moderate',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Abstract Factory',
  description: 'Provides an interface for creating families of related or dependent objects without specifying their concrete classes.',
  intent: 'Create families of related objects without coupling to their concrete implementations.',
  when_to_use: 'When a system must be independent of how its products are created, or when a system should work with multiple families of products.',
  when_not_to_use: 'When there is only one family of products or when adding new product types requires changing the abstract interface.',
  complexity: 'complex',
  frequency: 'occasional'
});

CREATE (p:Pattern {
  name: 'Builder',
  description: 'Separates the construction of a complex object from its representation, allowing the same construction process to create different representations.',
  intent: 'Construct complex objects step-by-step, allowing different representations from the same construction process.',
  when_to_use: 'When an object requires many optional parameters, when construction involves multiple steps, or when you want immutable objects built incrementally.',
  when_not_to_use: 'When objects are simple with few parameters, or when the construction process does not vary.',
  complexity: 'moderate',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Prototype',
  description: 'Creates new objects by copying an existing object, known as the prototype, rather than creating from scratch.',
  intent: 'Create new objects by cloning existing instances to avoid costly creation operations.',
  when_to_use: 'When object creation is expensive and similar objects are frequently needed, or when classes to instantiate are specified at runtime.',
  when_not_to_use: 'When objects have complex circular references that make deep copying difficult, or when creation cost is negligible.',
  complexity: 'moderate',
  frequency: 'occasional'
});

// =============================================================================
// 7. STRUCTURAL PATTERNS
// =============================================================================

CREATE (p:Pattern {
  name: 'Adapter',
  description: 'Converts the interface of a class into another interface clients expect. Lets classes work together that could not otherwise due to incompatible interfaces.',
  intent: 'Convert an incompatible interface into one that clients expect.',
  when_to_use: 'When integrating legacy code with new systems, wrapping third-party libraries, or when existing classes have incompatible interfaces.',
  when_not_to_use: 'When the interfaces are already compatible, or when a redesign of the interface would be more appropriate.',
  complexity: 'simple',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Bridge',
  description: 'Decouples an abstraction from its implementation so that the two can vary independently. Composes objects in tree structures.',
  intent: 'Separate abstraction from implementation so they can vary independently.',
  when_to_use: 'When both the abstraction and implementation need to be extended independently, or when implementation changes should not affect client code.',
  when_not_to_use: 'When the abstraction has only one possible implementation, or when the complexity of separation is not justified.',
  complexity: 'complex',
  frequency: 'occasional'
});

CREATE (p:Pattern {
  name: 'Composite',
  description: 'Composes objects into tree structures to represent part-whole hierarchies. Lets clients treat individual objects and compositions uniformly.',
  intent: 'Compose objects into tree structures and treat individual objects and compositions uniformly.',
  when_to_use: 'When representing part-whole hierarchies, when clients should treat composite and individual objects uniformly, such as file systems or UI components.',
  when_not_to_use: 'When the tree structure is not natural, or when leaf and composite objects need very different interfaces.',
  complexity: 'moderate',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Decorator',
  description: 'Attaches additional responsibilities to an object dynamically. Provides a flexible alternative to subclassing for extending functionality.',
  intent: 'Add responsibilities to objects dynamically without modifying their code.',
  when_to_use: 'When adding responsibilities to individual objects without affecting others, when extension by subclassing is impractical due to combinatorial explosion.',
  when_not_to_use: 'When the order of decoration matters and is hard to control, or when many small decorators create complexity in debugging.',
  complexity: 'moderate',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Facade',
  description: 'Provides a unified interface to a set of interfaces in a subsystem. Defines a higher-level interface that makes the subsystem easier to use.',
  intent: 'Provide a simplified interface to a complex subsystem.',
  when_to_use: 'When providing a simple interface to a complex subsystem, when decoupling clients from subsystem components, or when layering a system.',
  when_not_to_use: 'When the facade becomes a god object that couples to everything, or when clients need fine-grained access to subsystem features.',
  complexity: 'simple',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Proxy',
  description: 'Provides a surrogate or placeholder for another object to control access to it. Types include virtual, protection, and remote proxies.',
  intent: 'Control access to an object by providing a surrogate or placeholder.',
  when_to_use: 'When lazy initialization, access control, logging, or caching is needed around an object without changing its interface.',
  when_not_to_use: 'When the indirection adds latency without benefit, or when the original object is simple and always available.',
  complexity: 'moderate',
  frequency: 'common'
});

// =============================================================================
// 8. BEHAVIORAL PATTERNS
// =============================================================================

CREATE (p:Pattern {
  name: 'Observer',
  description: 'Defines a one-to-many dependency between objects so that when one object changes state, all its dependents are notified and updated automatically.',
  intent: 'Establish a subscription mechanism to notify multiple objects about events.',
  when_to_use: 'When changes to one object require changing others and you do not know how many objects need to change, event-driven architectures.',
  when_not_to_use: 'When the notification order matters and is hard to guarantee, or when cascading updates could cause performance issues.',
  complexity: 'moderate',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Strategy',
  description: 'Defines a family of algorithms, encapsulates each one, and makes them interchangeable. Lets the algorithm vary independently from clients.',
  intent: 'Define interchangeable algorithms and let clients choose at runtime.',
  when_to_use: 'When you need different variants of an algorithm, when a class has multiple conditional behaviors, or when you want to isolate algorithm logic.',
  when_not_to_use: 'When there are only two simple alternatives that rarely change.',
  complexity: 'simple',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Command',
  description: 'Encapsulates a request as an object, letting you parameterize clients with different requests, queue or log requests, and support undoable operations.',
  intent: 'Encapsulate requests as objects to support parameterization, queuing, logging, and undo.',
  when_to_use: 'When implementing undo/redo, task queues, macro recording, transactional behavior.',
  when_not_to_use: 'When requests are simple one-off operations that do not need queuing, logging, or undo support.',
  complexity: 'moderate',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'State',
  description: 'Allows an object to alter its behavior when its internal state changes. The object appears to change its class.',
  intent: 'Let an object change its behavior when its internal state changes.',
  when_to_use: 'When object behavior depends on its state and must change at runtime, when state-specific code is scattered across many conditionals.',
  when_not_to_use: 'When there are only two or three simple states, or when state transitions are trivial.',
  complexity: 'moderate',
  frequency: 'occasional'
});

CREATE (p:Pattern {
  name: 'Template Method',
  description: 'Defines the skeleton of an algorithm in a method, deferring some steps to subclasses without changing the algorithm structure.',
  intent: 'Define algorithm skeleton in a base class, letting subclasses override specific steps.',
  when_to_use: 'When multiple classes share the same algorithm structure but differ in specific steps.',
  when_not_to_use: 'When the algorithm has no invariant steps, or when composition via Strategy is more flexible.',
  complexity: 'simple',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Iterator',
  description: 'Provides a way to access the elements of an aggregate object sequentially without exposing its underlying representation.',
  intent: 'Traverse elements of a collection without exposing its internal structure.',
  when_to_use: 'When you need to traverse complex data structures without exposing their internals.',
  when_not_to_use: 'When the collection is simple and direct access is sufficient.',
  complexity: 'simple',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Chain of Responsibility',
  description: 'Avoids coupling the sender of a request to its receiver by giving more than one object a chance to handle it. Chains the receiving objects.',
  intent: 'Pass requests along a chain of handlers until one processes it.',
  when_to_use: 'When multiple objects may handle a request and the handler is not known a priori, middleware pipelines, validation chains.',
  when_not_to_use: 'When requests must always be handled and dropping them is unacceptable.',
  complexity: 'moderate',
  frequency: 'occasional'
});

CREATE (p:Pattern {
  name: 'Mediator',
  description: 'Defines an object that encapsulates how a set of objects interact. Promotes loose coupling by keeping objects from referring to each other explicitly.',
  intent: 'Centralize complex communications and control between related objects.',
  when_to_use: 'When objects communicate in complex ways creating tight coupling.',
  when_not_to_use: 'When the mediator becomes a god object, or when direct communication between a few objects is simpler.',
  complexity: 'moderate',
  frequency: 'occasional'
});

// =============================================================================
// 9. ARCHITECTURAL PATTERNS
// =============================================================================

CREATE (p:Pattern {
  name: 'Repository',
  description: 'Mediates between the domain and data mapping layers using a collection-like interface for accessing domain objects.',
  intent: 'Abstract data access behind a collection-like interface to decouple domain logic from persistence.',
  when_to_use: 'When domain logic should be independent of data access details, when testing requires mock data sources.',
  when_not_to_use: 'When the application is a simple CRUD with no domain logic, adding unnecessary abstraction.',
  complexity: 'simple',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Unit of Work',
  description: 'Maintains a list of objects affected by a business transaction and coordinates writing out changes and resolving concurrency problems.',
  intent: 'Track changes to objects during a transaction and coordinate persistence in a single batch.',
  when_to_use: 'When multiple objects must be persisted atomically, when tracking dirty objects for batch writes.',
  when_not_to_use: 'When each operation is independent and does not require transactional grouping.',
  complexity: 'complex',
  frequency: 'occasional'
});

CREATE (p:Pattern {
  name: 'CQRS',
  description: 'Command Query Responsibility Segregation separates read and write operations into different models, optimizing each independently.',
  intent: 'Separate read and write models to optimize each for its specific workload.',
  when_to_use: 'When read and write workloads have different performance or scaling requirements, when complex domain logic applies only to writes.',
  when_not_to_use: 'When read and write models are identical, in simple CRUD applications where the added complexity is not justified.',
  complexity: 'complex',
  frequency: 'occasional'
});

CREATE (p:Pattern {
  name: 'Event Sourcing',
  description: 'Stores all changes to application state as a sequence of events rather than storing current state. Events can be replayed to reconstruct any past state.',
  intent: 'Persist state changes as an immutable sequence of events for auditability and temporal queries.',
  when_to_use: 'When complete audit trails are required, when temporal queries or event replay are needed, when used with CQRS.',
  when_not_to_use: 'When eventual consistency is unacceptable, when storage costs of all events are prohibitive, in simple CRUD systems.',
  complexity: 'complex',
  frequency: 'rare'
});

CREATE (p:Pattern {
  name: 'Hexagonal Architecture',
  description: 'Ports and Adapters architecture that isolates the core domain from external concerns through ports (interfaces) and adapters (implementations).',
  intent: 'Isolate core business logic from external concerns using ports and adapters.',
  when_to_use: 'When the core domain must be testable in isolation, when multiple delivery mechanisms or data sources are needed.',
  when_not_to_use: 'In small applications where the port/adapter overhead exceeds the domain complexity.',
  complexity: 'complex',
  frequency: 'occasional'
});

CREATE (p:Pattern {
  name: 'Service Locator',
  description: 'Provides a centralized registry that returns service instances on demand, decoupling clients from concrete implementations.',
  intent: 'Provide a central registry for obtaining service instances at runtime.',
  when_to_use: 'When a DI container is unavailable, when services must be resolved dynamically at runtime.',
  when_not_to_use: 'When a proper DI container is available, as Service Locator hides dependencies and makes testing harder.',
  complexity: 'simple',
  frequency: 'occasional'
});

CREATE (p:Pattern {
  name: 'Dependency Injection Container',
  description: 'A framework that manages object creation and dependency resolution, automatically injecting dependencies into constructors or setters.',
  intent: 'Automate dependency resolution and object lifecycle management.',
  when_to_use: 'When managing complex dependency graphs, when consistent lifecycle management is needed across the application.',
  when_not_to_use: 'When the application has few dependencies and manual wiring is simpler.',
  complexity: 'moderate',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Circuit Breaker',
  description: 'Prevents an application from repeatedly trying an operation that is likely to fail, allowing it to recover gracefully from failures.',
  intent: 'Stop cascading failures by failing fast when a downstream service is unavailable.',
  when_to_use: 'When calling external services that may fail, in microservice architectures to prevent cascade failures.',
  when_not_to_use: 'When calling local in-process operations that cannot fail independently.',
  complexity: 'moderate',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Saga',
  description: 'Manages distributed transactions across multiple services using a sequence of local transactions with compensating actions for rollback.',
  intent: 'Coordinate distributed transactions without two-phase commit using compensating operations.',
  when_to_use: 'When business transactions span multiple microservices, when eventual consistency is acceptable.',
  when_not_to_use: 'When strong consistency with ACID transactions is required, when the number of steps makes compensation overly complex.',
  complexity: 'complex',
  frequency: 'occasional'
});

CREATE (p:Pattern {
  name: 'API Gateway',
  description: 'Provides a single entry point for all client requests, routing them to appropriate microservices and handling cross-cutting concerns.',
  intent: 'Provide a unified entry point that routes requests and handles cross-cutting concerns like auth, rate limiting, and aggregation.',
  when_to_use: 'In microservice architectures to simplify client interactions, when cross-cutting concerns need centralized management.',
  when_not_to_use: 'When a single monolithic backend handles all requests, or when the gateway becomes a bottleneck.',
  complexity: 'moderate',
  frequency: 'common'
});

// =============================================================================
// 10. CONCURRENCY PATTERNS
// =============================================================================

CREATE (p:Pattern {
  name: 'Producer-Consumer',
  description: 'Decouples components that produce data from those that consume it using a shared buffer or queue for asynchronous processing.',
  intent: 'Decouple data production from consumption using a shared buffer.',
  when_to_use: 'When producers and consumers operate at different rates, when buffering work for async processing.',
  when_not_to_use: 'When synchronous processing is required, or when the overhead of queue management exceeds the benefit.',
  complexity: 'moderate',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Actor Model',
  description: 'Concurrent computation model where actors are independent units that communicate exclusively through asynchronous message passing.',
  intent: 'Model concurrent computation as independent actors communicating via async messages.',
  when_to_use: 'When building highly concurrent systems, when shared mutable state must be avoided, in distributed systems.',
  when_not_to_use: 'When synchronous request-response is simpler, when the overhead of message passing is not justified.',
  complexity: 'complex',
  frequency: 'occasional'
});

CREATE (p:Pattern {
  name: 'Thread Pool',
  description: 'Manages a pool of reusable threads to execute tasks, reducing the overhead of thread creation and destruction.',
  intent: 'Reuse a fixed set of threads to execute many tasks efficiently.',
  when_to_use: 'When many short-lived tasks need concurrent execution, when thread creation overhead is significant.',
  when_not_to_use: 'When tasks are long-running and block threads, or when async IO is more appropriate.',
  complexity: 'moderate',
  frequency: 'common'
});

CREATE (p:Pattern {
  name: 'Read-Write Lock',
  description: 'Allows concurrent read access to a shared resource while ensuring exclusive access for writes, improving throughput in read-heavy scenarios.',
  intent: 'Allow concurrent reads while ensuring exclusive write access to shared resources.',
  when_to_use: 'When reads vastly outnumber writes and concurrent read access improves performance.',
  when_not_to_use: 'When writes are frequent and readers would starve, or when a simpler mutex suffices.',
  complexity: 'moderate',
  frequency: 'occasional'
});

CREATE (p:Pattern {
  name: 'Future/Promise',
  description: 'Represents a value that will be available in the future, allowing asynchronous computation to be composed and chained.',
  intent: 'Represent pending async computations that can be composed and chained.',
  when_to_use: 'When coordinating asynchronous operations, when composing non-blocking workflows.',
  when_not_to_use: 'When synchronous execution is simpler and performance is acceptable.',
  complexity: 'simple',
  frequency: 'common'
});

// =============================================================================
// 11. ANTI-PATTERNS
// =============================================================================

CREATE (:AntiPattern {name: 'God Object', description: 'A single class that knows too much or does too much, concentrating functionality that should be distributed.', why_bad: 'Violates SRP, creates tight coupling, makes testing and maintenance extremely difficult.', better_alternative: 'Decompose into focused classes following SRP, apply Facade for simplified interfaces.'});
CREATE (:AntiPattern {name: 'Spaghetti Code', description: 'Code with tangled control flow lacking clear structure, often from excessive goto or deeply nested conditionals.', why_bad: 'Unreadable, unmaintainable, impossible to test or debug effectively.', better_alternative: 'Apply Strategy, State, or Chain of Responsibility to organize control flow.'});
CREATE (:AntiPattern {name: 'Golden Hammer', description: 'Using a familiar technology or pattern for every problem regardless of fit.', why_bad: 'Forces inappropriate solutions, ignores better alternatives, leads to poor architecture.', better_alternative: 'Evaluate trade-offs per problem, choose patterns based on context not familiarity.'});
CREATE (:AntiPattern {name: 'Premature Optimization', description: 'Optimizing code before profiling identifies actual bottlenecks.', why_bad: 'Wastes time, adds complexity, often optimizes non-bottleneck code while missing real issues.', better_alternative: 'Profile first, apply KISS and YAGNI, optimize measured bottlenecks with data.'});
CREATE (:AntiPattern {name: 'Circular Dependency', description: 'Two or more modules depend on each other creating a cycle that prevents independent compilation and testing.', why_bad: 'Prevents modular deployment, complicates builds, makes the dependency graph unstable.', better_alternative: 'Apply Dependency Inversion, introduce interfaces or Mediator to break cycles.'});
CREATE (:AntiPattern {name: 'Service Locator Abuse', description: 'Overusing Service Locator as a global registry hiding true dependencies from constructors.', why_bad: 'Hides dependencies, makes testing difficult, creates implicit coupling.', better_alternative: 'Use explicit Dependency Injection via constructors.'});
CREATE (:AntiPattern {name: 'Singleton Abuse', description: 'Overusing Singleton pattern for convenience creating hidden global state throughout the application.', why_bad: 'Creates hidden coupling, makes testing difficult, prevents parallel execution.', better_alternative: 'Use Dependency Injection to manage lifecycle and scope explicitly.'});
CREATE (:AntiPattern {name: 'Callback Hell', description: 'Deeply nested callbacks making asynchronous code unreadable and error-prone.', why_bad: 'Unreadable, impossible to handle errors consistently, difficult to compose.', better_alternative: 'Use Future/Promise, async/await, or reactive streams.'});
CREATE (:AntiPattern {name: 'Anemic Domain Model', description: 'Domain objects that contain only data with no behavior, with all logic in service classes.', why_bad: 'Violates OOP principles, scatters domain logic, leads to procedural code in disguise.', better_alternative: 'Apply Repository and rich domain models where entities contain behavior.'});
CREATE (:AntiPattern {name: 'Big Ball of Mud', description: 'A system lacking discernible architecture where everything is intertwined with no clear boundaries.', why_bad: 'Impossible to understand, test, or evolve. Changes cause unpredictable side effects.', better_alternative: 'Apply Hexagonal Architecture, establish bounded contexts, introduce Facade layers.'});

// =============================================================================
// 12. BELONGS_TO RELATIONSHIPS (Pattern -> Category)
// =============================================================================

MATCH (p:Pattern {name: 'Singleton'}), (c:Category {name: 'creational'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Factory Method'}), (c:Category {name: 'creational'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Abstract Factory'}), (c:Category {name: 'creational'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Builder'}), (c:Category {name: 'creational'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Prototype'}), (c:Category {name: 'creational'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Adapter'}), (c:Category {name: 'structural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Bridge'}), (c:Category {name: 'structural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Composite'}), (c:Category {name: 'structural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Decorator'}), (c:Category {name: 'structural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Facade'}), (c:Category {name: 'structural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Proxy'}), (c:Category {name: 'structural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Observer'}), (c:Category {name: 'behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Strategy'}), (c:Category {name: 'behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Command'}), (c:Category {name: 'behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'State'}), (c:Category {name: 'behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Template Method'}), (c:Category {name: 'behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Iterator'}), (c:Category {name: 'behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Chain of Responsibility'}), (c:Category {name: 'behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Mediator'}), (c:Category {name: 'behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Repository'}), (c:Category {name: 'architectural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Unit of Work'}), (c:Category {name: 'architectural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'CQRS'}), (c:Category {name: 'architectural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Event Sourcing'}), (c:Category {name: 'architectural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Hexagonal Architecture'}), (c:Category {name: 'architectural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Service Locator'}), (c:Category {name: 'architectural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Dependency Injection Container'}), (c:Category {name: 'architectural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Circuit Breaker'}), (c:Category {name: 'architectural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Saga'}), (c:Category {name: 'architectural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'API Gateway'}), (c:Category {name: 'architectural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Producer-Consumer'}), (c:Category {name: 'concurrency'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Actor Model'}), (c:Category {name: 'concurrency'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Thread Pool'}), (c:Category {name: 'concurrency'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Read-Write Lock'}), (c:Category {name: 'concurrency'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Future/Promise'}), (c:Category {name: 'concurrency'}) CREATE (p)-[:BELONGS_TO]->(c);

// =============================================================================
// 13. TRADE-OFFS
// =============================================================================

MATCH (p:Pattern {name: 'Singleton'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'Controlled access to sole instance, reduced namespace pollution', cost: 'Difficult to test, hidden dependencies, violates SRP if overloaded', context: 'Acceptable for truly global resources like configuration or logging'});
MATCH (p:Pattern {name: 'Factory Method'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'Eliminates tight coupling to concrete classes, supports open/closed principle', cost: 'Requires additional class hierarchy, can lead to parallel hierarchies', context: 'Justified when creation logic varies by context or product type'});
MATCH (p:Pattern {name: 'Abstract Factory'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'Ensures consistent product families, isolates concrete classes', cost: 'Difficult to add new product types, increases class count significantly', context: 'Best when product families are stable and multiple families are needed'});
MATCH (p:Pattern {name: 'Builder'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'Readable construction of complex objects, immutability support', cost: 'Requires separate builder class per product, verbose for simple objects', context: 'Ideal when objects have many optional parameters or construction steps'});
MATCH (p:Pattern {name: 'Observer'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'Loose coupling between subject and observers, dynamic subscription', cost: 'Unexpected updates, memory leaks from forgotten subscriptions, debugging difficulty', context: 'Ideal for event-driven systems and UI data binding'});
MATCH (p:Pattern {name: 'Strategy'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'Runtime algorithm switching, eliminates conditionals, testable algorithms', cost: 'Clients must be aware of different strategies, increased number of objects', context: 'Best when algorithms change frequently or multiple variants coexist'});
MATCH (p:Pattern {name: 'Repository'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'Testable domain logic, swappable data sources, clean separation', cost: 'Additional abstraction layer, can become a leaky abstraction', context: 'Valuable in domain-driven design with complex business rules'});
MATCH (p:Pattern {name: 'CQRS'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'Independent scaling of reads and writes, optimized models', cost: 'Eventual consistency complexity, data synchronization overhead', context: 'Justified when read and write workloads differ significantly'});
MATCH (p:Pattern {name: 'Circuit Breaker'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'Prevents cascade failures, enables graceful degradation', cost: 'Adds latency for health checks, requires careful threshold tuning', context: 'Essential in microservice architectures calling external services'});
MATCH (p:Pattern {name: 'Saga'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'Distributed transactions without two-phase commit, service autonomy', cost: 'Compensating transactions are complex, eventual consistency', context: 'Required when business operations span multiple microservices'});
MATCH (p:Pattern {name: 'Decorator'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'Dynamic behavior addition, avoids subclass explosion', cost: 'Many small objects, decorator ordering matters, debugging complexity', context: 'Best for cross-cutting concerns like logging, caching, auth'});
MATCH (p:Pattern {name: 'Facade'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'Simplified interface, reduced client coupling to subsystem', cost: 'Can become a god object if not bounded, hides useful complexity', context: 'Ideal for providing clean APIs to complex subsystems'});
MATCH (p:Pattern {name: 'Command'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'Decouples invoker from executor, enables undo and queuing', cost: 'Increased number of classes, overhead for simple operations', context: 'Valuable for task queues, undo systems, and macro recording'});
MATCH (p:Pattern {name: 'Producer-Consumer'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'Decoupled throughput, buffered processing, rate smoothing', cost: 'Queue management overhead, potential memory issues, ordering complexity', context: 'Essential for async processing pipelines and rate-different components'});
MATCH (p:Pattern {name: 'Actor Model'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'No shared state, natural distribution, fault isolation', cost: 'Message passing overhead, debugging difficulty, potential mailbox overflow', context: 'Ideal for highly concurrent distributed systems'});
MATCH (p:Pattern {name: 'Hexagonal Architecture'}) CREATE (p)-[:HAS_TRADEOFF]->(:TradeOff {benefit: 'Testable core domain, technology-agnostic business logic, swappable adapters', cost: 'More interfaces and classes, indirection overhead, learning curve', context: 'Best for long-lived applications with evolving infrastructure needs'});

// =============================================================================
// 14. ANTI_PATTERN_OF RELATIONSHIPS
// =============================================================================

MATCH (p:Pattern {name: 'Singleton'}), (ap:AntiPattern {name: 'Singleton Abuse'}) CREATE (p)-[:ANTI_PATTERN_OF]->(ap);
MATCH (p:Pattern {name: 'Service Locator'}), (ap:AntiPattern {name: 'Service Locator Abuse'}) CREATE (p)-[:ANTI_PATTERN_OF]->(ap);
MATCH (p:Pattern {name: 'Facade'}), (ap:AntiPattern {name: 'God Object'}) CREATE (p)-[:ANTI_PATTERN_OF]->(ap);
MATCH (p:Pattern {name: 'Mediator'}), (ap:AntiPattern {name: 'God Object'}) CREATE (p)-[:ANTI_PATTERN_OF]->(ap);
MATCH (p:Pattern {name: 'Future/Promise'}), (ap:AntiPattern {name: 'Callback Hell'}) CREATE (p)-[:ANTI_PATTERN_OF]->(ap);
MATCH (p:Pattern {name: 'Repository'}), (ap:AntiPattern {name: 'Anemic Domain Model'}) CREATE (p)-[:ANTI_PATTERN_OF]->(ap);
MATCH (p:Pattern {name: 'Hexagonal Architecture'}), (ap:AntiPattern {name: 'Big Ball of Mud'}) CREATE (p)-[:ANTI_PATTERN_OF]->(ap);
MATCH (p:Pattern {name: 'Strategy'}), (ap:AntiPattern {name: 'Spaghetti Code'}) CREATE (p)-[:ANTI_PATTERN_OF]->(ap);
MATCH (p:Pattern {name: 'State'}), (ap:AntiPattern {name: 'Spaghetti Code'}) CREATE (p)-[:ANTI_PATTERN_OF]->(ap);
MATCH (p:Pattern {name: 'Dependency Injection Container'}), (ap:AntiPattern {name: 'Circular Dependency'}) CREATE (p)-[:ANTI_PATTERN_OF]->(ap);

// =============================================================================
// 15. SUPPORTS RELATIONSHIPS (Pattern -> Principle)
// =============================================================================

MATCH (p:Pattern {name: 'Strategy'}), (pr:Principle {name: 'OCP'}) CREATE (p)-[:SUPPORTS {how: 'New algorithms added without modifying existing code'}]->(pr);
MATCH (p:Pattern {name: 'Strategy'}), (pr:Principle {name: 'SRP'}) CREATE (p)-[:SUPPORTS {how: 'Each strategy encapsulates a single algorithm'}]->(pr);
MATCH (p:Pattern {name: 'Strategy'}), (pr:Principle {name: 'DIP'}) CREATE (p)-[:SUPPORTS {how: 'Clients depend on strategy interface, not implementations'}]->(pr);
MATCH (p:Pattern {name: 'Observer'}), (pr:Principle {name: 'OCP'}) CREATE (p)-[:SUPPORTS {how: 'New observers added without modifying the subject'}]->(pr);
MATCH (p:Pattern {name: 'Observer'}), (pr:Principle {name: 'DIP'}) CREATE (p)-[:SUPPORTS {how: 'Subject depends on observer interface, not concrete observers'}]->(pr);
MATCH (p:Pattern {name: 'Factory Method'}), (pr:Principle {name: 'OCP'}) CREATE (p)-[:SUPPORTS {how: 'New product types added by creating new factory subclasses'}]->(pr);
MATCH (p:Pattern {name: 'Factory Method'}), (pr:Principle {name: 'DIP'}) CREATE (p)-[:SUPPORTS {how: 'Client depends on factory interface not concrete products'}]->(pr);
MATCH (p:Pattern {name: 'Decorator'}), (pr:Principle {name: 'OCP'}) CREATE (p)-[:SUPPORTS {how: 'New behaviors added by wrapping without modifying original'}]->(pr);
MATCH (p:Pattern {name: 'Decorator'}), (pr:Principle {name: 'SRP'}) CREATE (p)-[:SUPPORTS {how: 'Each decorator handles one concern'}]->(pr);
MATCH (p:Pattern {name: 'Decorator'}), (pr:Principle {name: 'composition-over-inheritance'}) CREATE (p)-[:SUPPORTS {how: 'Composes behavior at runtime instead of compile-time inheritance'}]->(pr);
MATCH (p:Pattern {name: 'Repository'}), (pr:Principle {name: 'SRP'}) CREATE (p)-[:SUPPORTS {how: 'Separates data access from domain logic'}]->(pr);
MATCH (p:Pattern {name: 'Repository'}), (pr:Principle {name: 'DIP'}) CREATE (p)-[:SUPPORTS {how: 'Domain depends on repository interface not concrete data access'}]->(pr);
MATCH (p:Pattern {name: 'Repository'}), (pr:Principle {name: 'separation-of-concerns'}) CREATE (p)-[:SUPPORTS {how: 'Isolates persistence concern from business logic'}]->(pr);
MATCH (p:Pattern {name: 'Hexagonal Architecture'}), (pr:Principle {name: 'DIP'}) CREATE (p)-[:SUPPORTS {how: 'Core domain depends only on port interfaces, never on adapters'}]->(pr);
MATCH (p:Pattern {name: 'Hexagonal Architecture'}), (pr:Principle {name: 'separation-of-concerns'}) CREATE (p)-[:SUPPORTS {how: 'Strict boundaries between domain, ports, and adapters'}]->(pr);
MATCH (p:Pattern {name: 'Dependency Injection Container'}), (pr:Principle {name: 'DIP'}) CREATE (p)-[:SUPPORTS {how: 'Automates dependency inversion by injecting interfaces'}]->(pr);
MATCH (p:Pattern {name: 'Command'}), (pr:Principle {name: 'SRP'}) CREATE (p)-[:SUPPORTS {how: 'Each command encapsulates a single operation'}]->(pr);
MATCH (p:Pattern {name: 'Command'}), (pr:Principle {name: 'OCP'}) CREATE (p)-[:SUPPORTS {how: 'New commands added without modifying invoker'}]->(pr);
MATCH (p:Pattern {name: 'Adapter'}), (pr:Principle {name: 'OCP'}) CREATE (p)-[:SUPPORTS {how: 'Integrates new interfaces without modifying existing code'}]->(pr);
MATCH (p:Pattern {name: 'Adapter'}), (pr:Principle {name: 'ISP'}) CREATE (p)-[:SUPPORTS {how: 'Adapts only the interface methods the client needs'}]->(pr);
MATCH (p:Pattern {name: 'Facade'}), (pr:Principle {name: 'KISS'}) CREATE (p)-[:SUPPORTS {how: 'Simplifies complex subsystem interactions into a clean API'}]->(pr);
MATCH (p:Pattern {name: 'Iterator'}), (pr:Principle {name: 'SRP'}) CREATE (p)-[:SUPPORTS {how: 'Separates traversal responsibility from collection'}]->(pr);
MATCH (p:Pattern {name: 'Chain of Responsibility'}), (pr:Principle {name: 'OCP'}) CREATE (p)-[:SUPPORTS {how: 'New handlers added to chain without modifying existing ones'}]->(pr);
MATCH (p:Pattern {name: 'Chain of Responsibility'}), (pr:Principle {name: 'SRP'}) CREATE (p)-[:SUPPORTS {how: 'Each handler responsible for one type of processing'}]->(pr);
MATCH (p:Pattern {name: 'Template Method'}), (pr:Principle {name: 'DRY'}) CREATE (p)-[:SUPPORTS {how: 'Shared algorithm skeleton eliminates duplicate code in subclasses'}]->(pr);
MATCH (p:Pattern {name: 'Builder'}), (pr:Principle {name: 'SRP'}) CREATE (p)-[:SUPPORTS {how: 'Separates construction logic from the object representation'}]->(pr);
MATCH (p:Pattern {name: 'CQRS'}), (pr:Principle {name: 'SRP'}) CREATE (p)-[:SUPPORTS {how: 'Read and write models each have a single responsibility'}]->(pr);
MATCH (p:Pattern {name: 'CQRS'}), (pr:Principle {name: 'separation-of-concerns'}) CREATE (p)-[:SUPPORTS {how: 'Completely separates read and write concerns'}]->(pr);

// =============================================================================
// 16. VIOLATES RELATIONSHIPS (Pattern -> Principle)
// =============================================================================

MATCH (p:Pattern {name: 'Singleton'}), (pr:Principle {name: 'SRP'}) CREATE (p)-[:VIOLATES {when: 'When the singleton accumulates responsibilities beyond its core purpose', why: 'Global access point encourages adding unrelated functionality'}]->(pr);
MATCH (p:Pattern {name: 'Singleton'}), (pr:Principle {name: 'DIP'}) CREATE (p)-[:VIOLATES {when: 'When code directly references the singleton instead of an interface', why: 'Creates tight coupling to the concrete singleton class'}]->(pr);
MATCH (p:Pattern {name: 'Service Locator'}), (pr:Principle {name: 'DIP'}) CREATE (p)-[:VIOLATES {when: 'When used as a global registry hiding dependencies', why: 'Dependencies are resolved at runtime, not declared in constructors'}]->(pr);
MATCH (p:Pattern {name: 'Template Method'}), (pr:Principle {name: 'composition-over-inheritance'}) CREATE (p)-[:VIOLATES {when: 'Always, by design', why: 'Relies on inheritance to define algorithm variations'}]->(pr);
MATCH (p:Pattern {name: 'Mediator'}), (pr:Principle {name: 'SRP'}) CREATE (p)-[:VIOLATES {when: 'When the mediator grows to handle too many interactions', why: 'Centralizing communication can create a god object'}]->(pr);

// =============================================================================
// 17. RELATED_TO RELATIONSHIPS
// =============================================================================

MATCH (a:Pattern {name: 'Singleton'}), (b:Pattern {name: 'Factory Method'}) CREATE (a)-[:RELATED_TO {relationship_type: 'complementary'}]->(b);
MATCH (a:Pattern {name: 'Abstract Factory'}), (b:Pattern {name: 'Factory Method'}) CREATE (a)-[:RELATED_TO {relationship_type: 'alternative'}]->(b);
MATCH (a:Pattern {name: 'Builder'}), (b:Pattern {name: 'Abstract Factory'}) CREATE (a)-[:RELATED_TO {relationship_type: 'alternative'}]->(b);
MATCH (a:Pattern {name: 'Prototype'}), (b:Pattern {name: 'Factory Method'}) CREATE (a)-[:RELATED_TO {relationship_type: 'alternative'}]->(b);
MATCH (a:Pattern {name: 'Adapter'}), (b:Pattern {name: 'Facade'}) CREATE (a)-[:RELATED_TO {relationship_type: 'complementary'}]->(b);
MATCH (a:Pattern {name: 'Adapter'}), (b:Pattern {name: 'Bridge'}) CREATE (a)-[:RELATED_TO {relationship_type: 'alternative'}]->(b);
MATCH (a:Pattern {name: 'Decorator'}), (b:Pattern {name: 'Proxy'}) CREATE (a)-[:RELATED_TO {relationship_type: 'alternative'}]->(b);
MATCH (a:Pattern {name: 'Decorator'}), (b:Pattern {name: 'Strategy'}) CREATE (a)-[:RELATED_TO {relationship_type: 'alternative'}]->(b);
MATCH (a:Pattern {name: 'Composite'}), (b:Pattern {name: 'Iterator'}) CREATE (a)-[:RELATED_TO {relationship_type: 'complementary'}]->(b);
MATCH (a:Pattern {name: 'Composite'}), (b:Pattern {name: 'Decorator'}) CREATE (a)-[:RELATED_TO {relationship_type: 'complementary'}]->(b);
MATCH (a:Pattern {name: 'Observer'}), (b:Pattern {name: 'Mediator'}) CREATE (a)-[:RELATED_TO {relationship_type: 'alternative'}]->(b);
MATCH (a:Pattern {name: 'Strategy'}), (b:Pattern {name: 'State'}) CREATE (a)-[:RELATED_TO {relationship_type: 'alternative'}]->(b);
MATCH (a:Pattern {name: 'Strategy'}), (b:Pattern {name: 'Template Method'}) CREATE (a)-[:RELATED_TO {relationship_type: 'alternative'}]->(b);
MATCH (a:Pattern {name: 'Command'}), (b:Pattern {name: 'Strategy'}) CREATE (a)-[:RELATED_TO {relationship_type: 'complementary'}]->(b);
MATCH (a:Pattern {name: 'Chain of Responsibility'}), (b:Pattern {name: 'Decorator'}) CREATE (a)-[:RELATED_TO {relationship_type: 'complementary'}]->(b);
MATCH (a:Pattern {name: 'Repository'}), (b:Pattern {name: 'Unit of Work'}) CREATE (a)-[:RELATED_TO {relationship_type: 'complementary'}]->(b);
MATCH (a:Pattern {name: 'CQRS'}), (b:Pattern {name: 'Event Sourcing'}) CREATE (a)-[:RELATED_TO {relationship_type: 'complementary'}]->(b);
MATCH (a:Pattern {name: 'CQRS'}), (b:Pattern {name: 'Repository'}) CREATE (a)-[:RELATED_TO {relationship_type: 'complementary'}]->(b);
MATCH (a:Pattern {name: 'Saga'}), (b:Pattern {name: 'Event Sourcing'}) CREATE (a)-[:RELATED_TO {relationship_type: 'complementary'}]->(b);
MATCH (a:Pattern {name: 'Circuit Breaker'}), (b:Pattern {name: 'API Gateway'}) CREATE (a)-[:RELATED_TO {relationship_type: 'complementary'}]->(b);
MATCH (a:Pattern {name: 'Hexagonal Architecture'}), (b:Pattern {name: 'Repository'}) CREATE (a)-[:RELATED_TO {relationship_type: 'complementary'}]->(b);
MATCH (a:Pattern {name: 'Hexagonal Architecture'}), (b:Pattern {name: 'Dependency Injection Container'}) CREATE (a)-[:RELATED_TO {relationship_type: 'prerequisite'}]->(b);
MATCH (a:Pattern {name: 'Dependency Injection Container'}), (b:Pattern {name: 'Service Locator'}) CREATE (a)-[:RELATED_TO {relationship_type: 'alternative'}]->(b);
MATCH (a:Pattern {name: 'Producer-Consumer'}), (b:Pattern {name: 'Command'}) CREATE (a)-[:RELATED_TO {relationship_type: 'complementary'}]->(b);
MATCH (a:Pattern {name: 'Actor Model'}), (b:Pattern {name: 'Observer'}) CREATE (a)-[:RELATED_TO {relationship_type: 'alternative'}]->(b);
MATCH (a:Pattern {name: 'Future/Promise'}), (b:Pattern {name: 'Observer'}) CREATE (a)-[:RELATED_TO {relationship_type: 'complementary'}]->(b);
MATCH (a:Pattern {name: 'Thread Pool'}), (b:Pattern {name: 'Producer-Consumer'}) CREATE (a)-[:RELATED_TO {relationship_type: 'complementary'}]->(b);

// =============================================================================
// 18. COMMONLY_USED_WITH RELATIONSHIPS
// =============================================================================

MATCH (a:Pattern {name: 'Repository'}), (b:Pattern {name: 'Unit of Work'}) CREATE (a)-[:COMMONLY_USED_WITH {frequency: 'common', example_context: 'Data access layer in DDD applications'}]->(b);
MATCH (a:Pattern {name: 'CQRS'}), (b:Pattern {name: 'Event Sourcing'}) CREATE (a)-[:COMMONLY_USED_WITH {frequency: 'common', example_context: 'Event-driven microservice architectures'}]->(b);
MATCH (a:Pattern {name: 'Circuit Breaker'}), (b:Pattern {name: 'API Gateway'}) CREATE (a)-[:COMMONLY_USED_WITH {frequency: 'common', example_context: 'Resilient microservice communication'}]->(b);
MATCH (a:Pattern {name: 'Factory Method'}), (b:Pattern {name: 'Strategy'}) CREATE (a)-[:COMMONLY_USED_WITH {frequency: 'common', example_context: 'Creating strategy instances based on configuration'}]->(b);
MATCH (a:Pattern {name: 'Observer'}), (b:Pattern {name: 'Command'}) CREATE (a)-[:COMMONLY_USED_WITH {frequency: 'occasional', example_context: 'Event-sourced systems with command handling'}]->(b);
MATCH (a:Pattern {name: 'Decorator'}), (b:Pattern {name: 'Chain of Responsibility'}) CREATE (a)-[:COMMONLY_USED_WITH {frequency: 'occasional', example_context: 'Middleware pipelines in web frameworks'}]->(b);
MATCH (a:Pattern {name: 'Builder'}), (b:Pattern {name: 'Facade'}) CREATE (a)-[:COMMONLY_USED_WITH {frequency: 'occasional', example_context: 'Building complex configuration objects behind a simple API'}]->(b);
MATCH (a:Pattern {name: 'Hexagonal Architecture'}), (b:Pattern {name: 'Dependency Injection Container'}) CREATE (a)-[:COMMONLY_USED_WITH {frequency: 'common', example_context: 'Wiring adapters to ports in clean architecture'}]->(b);
MATCH (a:Pattern {name: 'Saga'}), (b:Pattern {name: 'Command'}) CREATE (a)-[:COMMONLY_USED_WITH {frequency: 'common', example_context: 'Orchestrating distributed transactions via command objects'}]->(b);
MATCH (a:Pattern {name: 'Producer-Consumer'}), (b:Pattern {name: 'Thread Pool'}) CREATE (a)-[:COMMONLY_USED_WITH {frequency: 'common', example_context: 'Worker pool consuming from task queue'}]->(b);

// =============================================================================
// 19. EVOLVES_TO RELATIONSHIPS
// =============================================================================

MATCH (a:Pattern {name: 'Factory Method'}), (b:Pattern {name: 'Abstract Factory'}) CREATE (a)-[:EVOLVES_TO {when: 'When multiple related product families emerge'}]->(b);
MATCH (a:Pattern {name: 'Strategy'}), (b:Pattern {name: 'State'}) CREATE (a)-[:EVOLVES_TO {when: 'When algorithm selection depends on object state transitions'}]->(b);
MATCH (a:Pattern {name: 'Observer'}), (b:Pattern {name: 'Event Sourcing'}) CREATE (a)-[:EVOLVES_TO {when: 'When events need persistence and replay capability'}]->(b);
MATCH (a:Pattern {name: 'Repository'}), (b:Pattern {name: 'CQRS'}) CREATE (a)-[:EVOLVES_TO {when: 'When read and write performance requirements diverge significantly'}]->(b);
MATCH (a:Pattern {name: 'Facade'}), (b:Pattern {name: 'API Gateway'}) CREATE (a)-[:EVOLVES_TO {when: 'When the system transitions from monolith to microservices'}]->(b);
MATCH (a:Pattern {name: 'Service Locator'}), (b:Pattern {name: 'Dependency Injection Container'}) CREATE (a)-[:EVOLVES_TO {when: 'When explicit dependency declaration becomes necessary for testability'}]->(b);
MATCH (a:Pattern {name: 'Template Method'}), (b:Pattern {name: 'Strategy'}) CREATE (a)-[:EVOLVES_TO {when: 'When inheritance-based variation needs to become composition-based'}]->(b);
MATCH (a:Pattern {name: 'Thread Pool'}), (b:Pattern {name: 'Actor Model'}) CREATE (a)-[:EVOLVES_TO {when: 'When shared state becomes a bottleneck and message-passing is preferable'}]->(b);
MATCH (a:Pattern {name: 'Singleton'}), (b:Pattern {name: 'Dependency Injection Container'}) CREATE (a)-[:EVOLVES_TO {when: 'When global state needs proper lifecycle management and testability'}]->(b);

// =============================================================================
// 20. IMPLEMENTATIONS (Pattern -> Implementation -> Language)
// =============================================================================

// --- Singleton ---
MATCH (p:Pattern {name: 'Singleton'}), (l:Language {name: 'python'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'class Singleton:\n    _instance = None\n\n    def __new__(cls):\n        if cls._instance is None:\n            cls._instance = super().__new__(cls)\n        return cls._instance\n\n    def __init__(self):\n        if not hasattr(self, \"_initialized\"):\n            self._initialized = True',
  notes: 'Thread-safe variant uses threading.Lock in __new__. Prefer module-level instance or dependency injection.',
  idioms: 'Module-level instance is the Pythonic singleton. __new__ override for class-based.',
  caveats: 'Not thread-safe by default. Subclassing can break the pattern. Testing requires reset mechanism.'
})-[:FOR_LANGUAGE]->(l);

MATCH (p:Pattern {name: 'Singleton'}), (l:Language {name: 'go'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'package config\n\nimport \"sync\"\n\ntype Config struct {\n    Value string\n}\n\nvar (\n    instance *Config\n    once     sync.Once\n)\n\nfunc GetInstance() *Config {\n    once.Do(func() {\n        instance = &Config{Value: \"default\"}\n    })\n    return instance\n}',
  notes: 'sync.Once guarantees thread-safe lazy initialization. Idiomatic Go pattern.',
  idioms: 'Use sync.Once for goroutine-safe initialization. Package-level var is common.',
  caveats: 'No way to reset for testing without build tags or interfaces.'
})-[:FOR_LANGUAGE]->(l);

// --- Factory Method ---
MATCH (p:Pattern {name: 'Factory Method'}), (l:Language {name: 'python'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'from abc import ABC, abstractmethod\n\nclass Transport(ABC):\n    @abstractmethod\n    def deliver(self) -> str: ...\n\nclass Truck(Transport):\n    def deliver(self) -> str:\n        return \"by road\"\n\nclass Ship(Transport):\n    def deliver(self) -> str:\n        return \"by sea\"\n\ndef create_transport(kind: str) -> Transport:\n    factories = {\"road\": Truck, \"sea\": Ship}\n    return factories[kind]()',
  notes: 'Python often uses a dict mapping instead of class hierarchy for factories.',
  idioms: 'Dict-based dispatch is idiomatic. ABC for interface enforcement.',
  caveats: 'KeyError on unknown kind needs handling. Consider Enum for type safety.'
})-[:FOR_LANGUAGE]->(l);

MATCH (p:Pattern {name: 'Factory Method'}), (l:Language {name: 'go'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'type Transport interface {\n    Deliver() string\n}\n\ntype Truck struct{}\nfunc (t Truck) Deliver() string { return \"by road\" }\n\ntype Ship struct{}\nfunc (s Ship) Deliver() string { return \"by sea\" }\n\nfunc NewTransport(kind string) Transport {\n    switch kind {\n    case \"road\":\n        return Truck{}\n    case \"sea\":\n        return Ship{}\n    default:\n        return nil\n    }\n}',
  notes: 'Go uses constructor functions (NewXxx) as factory methods idiomatically.',
  idioms: 'Interface-based polymorphism with constructor functions.',
  caveats: 'Return error instead of nil for unknown types in production code.'
})-[:FOR_LANGUAGE]->(l);

// --- Observer ---
MATCH (p:Pattern {name: 'Observer'}), (l:Language {name: 'python'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'from typing import Callable, List\n\nclass EventEmitter:\n    def __init__(self):\n        self._listeners: dict[str, List[Callable]] = {}\n\n    def on(self, event: str, callback: Callable):\n        self._listeners.setdefault(event, []).append(callback)\n\n    def emit(self, event: str, *args, **kwargs):\n        for cb in self._listeners.get(event, []):\n            cb(*args, **kwargs)',
  notes: 'Callback-based observer is the most Pythonic approach. Consider weakref for preventing memory leaks.',
  idioms: 'Dict of event -> callback list. Signals library for larger apps.',
  caveats: 'Callbacks hold strong references. Use weakref or explicit unsubscribe to prevent leaks.'
})-[:FOR_LANGUAGE]->(l);

MATCH (p:Pattern {name: 'Observer'}), (l:Language {name: 'typescript'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'type Listener<T> = (data: T) => void;\n\nclass EventEmitter<T> {\n  private listeners: Map<string, Listener<T>[]> = new Map();\n\n  on(event: string, listener: Listener<T>): void {\n    const list = this.listeners.get(event) ?? [];\n    list.push(listener);\n    this.listeners.set(event, list);\n  }\n\n  emit(event: string, data: T): void {\n    for (const listener of this.listeners.get(event) ?? []) {\n      listener(data);\n    }\n  }\n}',
  notes: 'Generic type parameter makes it type-safe. Node.js EventEmitter is the standard implementation.',
  idioms: 'Generics for type safety. Map for event storage. Optional chaining.',
  caveats: 'No automatic cleanup. Consider AbortController for subscription management.'
})-[:FOR_LANGUAGE]->(l);

// --- Strategy ---
MATCH (p:Pattern {name: 'Strategy'}), (l:Language {name: 'python'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'from typing import Protocol\n\nclass Compressor(Protocol):\n    def compress(self, data: bytes) -> bytes: ...\n\nclass GzipCompressor:\n    def compress(self, data: bytes) -> bytes:\n        import gzip\n        return gzip.compress(data)\n\nclass LZ4Compressor:\n    def compress(self, data: bytes) -> bytes:\n        return data  # placeholder\n\ndef process(data: bytes, strategy: Compressor) -> bytes:\n    return strategy.compress(data)',
  notes: 'Protocol-based structural typing is the modern Python approach.',
  idioms: 'Protocol for structural subtyping. Functions as strategies via callables.',
  caveats: 'Protocol requires Python 3.8+. Plain callables often suffice.'
})-[:FOR_LANGUAGE]->(l);

MATCH (p:Pattern {name: 'Strategy'}), (l:Language {name: 'go'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'type Compressor interface {\n    Compress(data []byte) ([]byte, error)\n}\n\ntype GzipCompressor struct{}\nfunc (g GzipCompressor) Compress(data []byte) ([]byte, error) {\n    // gzip implementation\n    return data, nil\n}\n\nfunc Process(data []byte, c Compressor) ([]byte, error) {\n    return c.Compress(data)\n}',
  notes: 'Go interfaces are implicitly satisfied, making Strategy natural.',
  idioms: 'Interface-based. Function types also work as single-method strategies.',
  caveats: 'Consider using a function type instead of interface for single methods.'
})-[:FOR_LANGUAGE]->(l);

// --- Repository ---
MATCH (p:Pattern {name: 'Repository'}), (l:Language {name: 'python'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'from abc import ABC, abstractmethod\nfrom typing import Optional, List\n\nclass UserRepository(ABC):\n    @abstractmethod\n    def get(self, user_id: str) -> Optional[dict]: ...\n    @abstractmethod\n    def save(self, user: dict) -> None: ...\n    @abstractmethod\n    def delete(self, user_id: str) -> None: ...\n    @abstractmethod\n    def list_all(self) -> List[dict]: ...\n\nclass PostgresUserRepository(UserRepository):\n    def __init__(self, conn):\n        self._conn = conn\n    def get(self, user_id: str) -> Optional[dict]:\n        return self._conn.execute(\"SELECT * FROM users WHERE id = %s\", (user_id,)).fetchone()\n    def save(self, user: dict) -> None:\n        self._conn.execute(\"INSERT INTO users ...\", user)\n    def delete(self, user_id: str) -> None:\n        self._conn.execute(\"DELETE FROM users WHERE id = %s\", (user_id,))\n    def list_all(self) -> List[dict]:\n        return self._conn.execute(\"SELECT * FROM users\").fetchall()',
  notes: 'ABC defines the contract. Concrete implementation encapsulates SQL. Use dataclasses for entities.',
  idioms: 'ABC for interface, dataclass for entities, context manager for transactions.',
  caveats: 'Avoid leaking ORM-specific query objects through the interface.'
})-[:FOR_LANGUAGE]->(l);

MATCH (p:Pattern {name: 'Repository'}), (l:Language {name: 'go'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'type User struct {\n    ID   string\n    Name string\n}\n\ntype UserRepository interface {\n    Get(id string) (*User, error)\n    Save(user *User) error\n    Delete(id string) error\n    List() ([]*User, error)\n}\n\ntype PostgresUserRepo struct {\n    db *sql.DB\n}\n\nfunc (r *PostgresUserRepo) Get(id string) (*User, error) {\n    row := r.db.QueryRow(\"SELECT id, name FROM users WHERE id=$1\", id)\n    u := &User{}\n    err := row.Scan(&u.ID, &u.Name)\n    return u, err\n}',
  notes: 'Interface defines contract. Struct implements it with concrete DB access.',
  idioms: 'Accept interfaces, return structs. Error as second return value.',
  caveats: 'Avoid returning *sql.Rows through the interface. Map to domain types.'
})-[:FOR_LANGUAGE]->(l);

// --- Circuit Breaker ---
MATCH (p:Pattern {name: 'Circuit Breaker'}), (l:Language {name: 'python'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'import time\nfrom enum import Enum\n\nclass State(Enum):\n    CLOSED = \"closed\"\n    OPEN = \"open\"\n    HALF_OPEN = \"half_open\"\n\nclass CircuitBreaker:\n    def __init__(self, threshold=5, timeout=30):\n        self.state = State.CLOSED\n        self.failures = 0\n        self.threshold = threshold\n        self.timeout = timeout\n        self.last_failure = 0.0\n\n    def call(self, func, *args, **kwargs):\n        if self.state == State.OPEN:\n            if time.time() - self.last_failure > self.timeout:\n                self.state = State.HALF_OPEN\n            else:\n                raise Exception(\"Circuit is OPEN\")\n        try:\n            result = func(*args, **kwargs)\n            self._on_success()\n            return result\n        except Exception as e:\n            self._on_failure()\n            raise\n\n    def _on_success(self):\n        self.failures = 0\n        self.state = State.CLOSED\n\n    def _on_failure(self):\n        self.failures += 1\n        self.last_failure = time.time()\n        if self.failures >= self.threshold:\n            self.state = State.OPEN',
  notes: 'Three states: closed (normal), open (failing fast), half-open (testing recovery).',
  idioms: 'Enum for state. Decorator variant wraps functions transparently.',
  caveats: 'Not thread-safe without locks. Consider tenacity library for production.'
})-[:FOR_LANGUAGE]->(l);

MATCH (p:Pattern {name: 'Circuit Breaker'}), (l:Language {name: 'go'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'type CircuitBreaker struct {\n    mu        sync.Mutex\n    failures  int\n    threshold int\n    timeout   time.Duration\n    state     string\n    lastFail  time.Time\n}\n\nfunc (cb *CircuitBreaker) Call(fn func() error) error {\n    cb.mu.Lock()\n    defer cb.mu.Unlock()\n    if cb.state == \"open\" {\n        if time.Since(cb.lastFail) > cb.timeout {\n            cb.state = \"half_open\"\n        } else {\n            return errors.New(\"circuit is open\")\n        }\n    }\n    if err := fn(); err != nil {\n        cb.failures++\n        cb.lastFail = time.Now()\n        if cb.failures >= cb.threshold {\n            cb.state = \"open\"\n        }\n        return err\n    }\n    cb.failures = 0\n    cb.state = \"closed\"\n    return nil\n}',
  notes: 'Mutex-protected for goroutine safety. sony/gobreaker is the production library.',
  idioms: 'Mutex for concurrency. Function parameter for the callable.',
  caveats: 'Use sony/gobreaker or similar library in production for metrics and callbacks.'
})-[:FOR_LANGUAGE]->(l);

// --- Builder ---
MATCH (p:Pattern {name: 'Builder'}), (l:Language {name: 'python'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'class QueryBuilder:\n    def __init__(self):\n        self._table = \"\"\n        self._conditions = []\n        self._limit = None\n\n    def table(self, name: str) -> \"QueryBuilder\":\n        self._table = name\n        return self\n\n    def where(self, condition: str) -> \"QueryBuilder\":\n        self._conditions.append(condition)\n        return self\n\n    def limit(self, n: int) -> \"QueryBuilder\":\n        self._limit = n\n        return self\n\n    def build(self) -> str:\n        sql = f\"SELECT * FROM {self._table}\"\n        if self._conditions:\n            sql += \" WHERE \" + \" AND \".join(self._conditions)\n        if self._limit:\n            sql += f\" LIMIT {self._limit}\"\n        return sql',
  notes: 'Method chaining via return self. Build method produces the final object.',
  idioms: 'Return self for chaining. Separate build() for validation.',
  caveats: 'Mutable builder allows reuse but can cause subtle bugs. Consider frozen dataclass for result.'
})-[:FOR_LANGUAGE]->(l);

MATCH (p:Pattern {name: 'Builder'}), (l:Language {name: 'rust'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'struct Query {\n    table: String,\n    conditions: Vec<String>,\n    limit: Option<usize>,\n}\n\nstruct QueryBuilder {\n    table: String,\n    conditions: Vec<String>,\n    limit: Option<usize>,\n}\n\nimpl QueryBuilder {\n    fn new(table: &str) -> Self {\n        Self { table: table.to_string(), conditions: vec![], limit: None }\n    }\n    fn where_clause(mut self, cond: &str) -> Self {\n        self.conditions.push(cond.to_string());\n        self\n    }\n    fn limit(mut self, n: usize) -> Self {\n        self.limit = Some(n);\n        self\n    }\n    fn build(self) -> Query {\n        Query { table: self.table, conditions: self.conditions, limit: self.limit }\n    }\n}',
  notes: 'Ownership-based builder consumes self, preventing reuse after build.',
  idioms: 'Take self by value for consuming builder. Option for optional fields.',
  caveats: 'Consuming self prevents accidental reuse. Use &mut self if reuse is needed.'
})-[:FOR_LANGUAGE]->(l);

// --- Decorator ---
MATCH (p:Pattern {name: 'Decorator'}), (l:Language {name: 'python'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'import functools\nimport time\n\ndef retry(max_attempts: int = 3):\n    def decorator(func):\n        @functools.wraps(func)\n        def wrapper(*args, **kwargs):\n            for attempt in range(max_attempts):\n                try:\n                    return func(*args, **kwargs)\n                except Exception:\n                    if attempt == max_attempts - 1:\n                        raise\n                    time.sleep(2 ** attempt)\n        return wrapper\n    return decorator\n\n@retry(max_attempts=3)\ndef fetch_data(url: str) -> dict:\n    pass',
  notes: 'Python decorators are the language-native implementation of this pattern.',
  idioms: 'functools.wraps preserves metadata. Parameterized decorators use nested functions.',
  caveats: 'Decorator stacking order matters. Use functools.wraps to preserve function metadata.'
})-[:FOR_LANGUAGE]->(l);

MATCH (p:Pattern {name: 'Decorator'}), (l:Language {name: 'typescript'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'interface DataSource {\n  read(): string;\n}\n\nclass FileDataSource implements DataSource {\n  read(): string { return \"raw data\"; }\n}\n\nclass EncryptionDecorator implements DataSource {\n  constructor(private wrapped: DataSource) {}\n  read(): string {\n    const data = this.wrapped.read();\n    return `encrypted(${data})`;\n  }\n}\n\nclass CompressionDecorator implements DataSource {\n  constructor(private wrapped: DataSource) {}\n  read(): string {\n    const data = this.wrapped.read();\n    return `compressed(${data})`;\n  }\n}',
  notes: 'Wrapper classes implementing the same interface. Compose at construction time.',
  idioms: 'Interface-based wrapping. Constructor injection of the wrapped component.',
  caveats: 'Each decorator must implement the full interface. Consider Proxy for transparent wrapping.'
})-[:FOR_LANGUAGE]->(l);

// --- Command ---
MATCH (p:Pattern {name: 'Command'}), (l:Language {name: 'python'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'from abc import ABC, abstractmethod\nfrom typing import List\n\nclass Command(ABC):\n    @abstractmethod\n    def execute(self) -> None: ...\n    @abstractmethod\n    def undo(self) -> None: ...\n\nclass InsertText(Command):\n    def __init__(self, doc: list, pos: int, text: str):\n        self.doc, self.pos, self.text = doc, pos, text\n    def execute(self):\n        self.doc.insert(self.pos, self.text)\n    def undo(self):\n        self.doc.pop(self.pos)\n\nclass CommandHistory:\n    def __init__(self):\n        self._history: List[Command] = []\n    def execute(self, cmd: Command):\n        cmd.execute()\n        self._history.append(cmd)\n    def undo(self):\n        if self._history:\n            self._history.pop().undo()',
  notes: 'Command with undo support. History tracks executed commands for rollback.',
  idioms: 'ABC for command interface. List as history stack.',
  caveats: 'Undo requires storing enough state to reverse the operation. Memory usage grows with history.'
})-[:FOR_LANGUAGE]->(l);

MATCH (p:Pattern {name: 'Command'}), (l:Language {name: 'java'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'public interface Command {\n    void execute();\n    void undo();\n}\n\npublic class InsertText implements Command {\n    private final List<String> doc;\n    private final int pos;\n    private final String text;\n\n    public InsertText(List<String> doc, int pos, String text) {\n        this.doc = doc; this.pos = pos; this.text = text;\n    }\n    public void execute() { doc.add(pos, text); }\n    public void undo() { doc.remove(pos); }\n}',
  notes: 'Classic OOP command pattern. Java has strong interface support.',
  idioms: 'Interface for command contract. Immutable fields via final.',
  caveats: 'Can lead to many small command classes. Consider lambdas for simple commands in Java 8+.'
})-[:FOR_LANGUAGE]->(l);

// --- Producer-Consumer ---
MATCH (p:Pattern {name: 'Producer-Consumer'}), (l:Language {name: 'python'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'import asyncio\n\nasync def producer(queue: asyncio.Queue, items: list):\n    for item in items:\n        await queue.put(item)\n    await queue.put(None)  # sentinel\n\nasync def consumer(queue: asyncio.Queue):\n    while True:\n        item = await queue.get()\n        if item is None:\n            break\n        print(f\"Processing: {item}\")\n        queue.task_done()\n\nasync def main():\n    queue = asyncio.Queue(maxsize=10)\n    await asyncio.gather(\n        producer(queue, [\"a\", \"b\", \"c\"]),\n        consumer(queue)\n    )',
  notes: 'asyncio.Queue for async producer-consumer. Use queue.Queue for threading.',
  idioms: 'Sentinel value (None) for shutdown. maxsize for backpressure.',
  caveats: 'Sentinel approach requires careful handling with multiple consumers.'
})-[:FOR_LANGUAGE]->(l);

MATCH (p:Pattern {name: 'Producer-Consumer'}), (l:Language {name: 'go'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'func producer(ch chan<- string, items []string) {\n    for _, item := range items {\n        ch <- item\n    }\n    close(ch)\n}\n\nfunc consumer(ch <-chan string) {\n    for item := range ch {\n        fmt.Printf(\"Processing: %s\\n\", item)\n    }\n}\n\nfunc main() {\n    ch := make(chan string, 10)\n    go producer(ch, []string{\"a\", \"b\", \"c\"})\n    consumer(ch)\n}',
  notes: 'Channels are Go\\'s native producer-consumer mechanism. Buffered for async.',
  idioms: 'Buffered channels. close() signals completion. range for consuming.',
  caveats: 'Unbuffered channels block. Use select with context for cancellation.'
})-[:FOR_LANGUAGE]->(l);

// --- Future/Promise ---
MATCH (p:Pattern {name: 'Future/Promise'}), (l:Language {name: 'python'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'import asyncio\n\nasync def fetch_user(user_id: str) -> dict:\n    await asyncio.sleep(0.1)  # simulate IO\n    return {\"id\": user_id, \"name\": \"Alice\"}\n\nasync def fetch_orders(user_id: str) -> list:\n    await asyncio.sleep(0.1)\n    return [{\"id\": \"ord1\", \"amount\": 42.0}]\n\nasync def main():\n    user_task = asyncio.create_task(fetch_user(\"u1\"))\n    orders_task = asyncio.create_task(fetch_orders(\"u1\"))\n    user, orders = await asyncio.gather(user_task, orders_task)\n    print(user, orders)',
  notes: 'asyncio.Task is Python\\'s Future/Promise. gather for concurrent composition.',
  idioms: 'create_task for concurrent execution. gather for joining.',
  caveats: 'Exceptions propagate on await. Use return_exceptions=True in gather for partial failure handling.'
})-[:FOR_LANGUAGE]->(l);

MATCH (p:Pattern {name: 'Future/Promise'}), (l:Language {name: 'rust'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'use tokio;\n\nasync fn fetch_user(id: &str) -> String {\n    tokio::time::sleep(std::time::Duration::from_millis(100)).await;\n    format!(\"User: {}\", id)\n}\n\nasync fn fetch_orders(id: &str) -> Vec<String> {\n    tokio::time::sleep(std::time::Duration::from_millis(100)).await;\n    vec![format!(\"Order for {}\", id)]\n}\n\n#[tokio::main]\nasync fn main() {\n    let (user, orders) = tokio::join!(\n        fetch_user(\"u1\"),\n        fetch_orders(\"u1\")\n    );\n    println!(\"{} {:?}\", user, orders);\n}',
  notes: 'Rust futures are lazy and zero-cost. tokio::join! for concurrent execution.',
  idioms: 'async/await with tokio runtime. join! macro for concurrent composition.',
  caveats: 'Futures are lazy - they do nothing until awaited. Pin is needed for self-referential futures.'
})-[:FOR_LANGUAGE]->(l);

// --- CQRS ---
MATCH (p:Pattern {name: 'CQRS'}), (l:Language {name: 'python'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'from dataclasses import dataclass\nfrom abc import ABC, abstractmethod\n\n@dataclass\nclass CreateUser:\n    name: str\n    email: str\n\nclass CommandHandler(ABC):\n    @abstractmethod\n    def handle(self, command) -> None: ...\n\nclass CreateUserHandler(CommandHandler):\n    def __init__(self, write_db):\n        self._db = write_db\n    def handle(self, cmd: CreateUser):\n        self._db.insert({\"name\": cmd.name, \"email\": cmd.email})\n\nclass UserQueryService:\n    def __init__(self, read_db):\n        self._db = read_db\n    def get_user(self, user_id: str) -> dict:\n        return self._db.find_one({\"id\": user_id})',
  notes: 'Separate command handlers (write) from query services (read). Different DB connections possible.',
  idioms: 'Dataclass commands. Separate handler and query service classes.',
  caveats: 'Synchronizing read and write models adds complexity. Consider event-driven sync.'
})-[:FOR_LANGUAGE]->(l);

MATCH (p:Pattern {name: 'CQRS'}), (l:Language {name: 'go'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'type CreateUserCmd struct {\n    Name  string\n    Email string\n}\n\ntype CommandHandler interface {\n    Handle(cmd interface{}) error\n}\n\ntype CreateUserHandler struct {\n    writeDB *sql.DB\n}\n\nfunc (h *CreateUserHandler) Handle(cmd interface{}) error {\n    c := cmd.(CreateUserCmd)\n    _, err := h.writeDB.Exec(\"INSERT INTO users (name, email) VALUES ($1, $2)\", c.Name, c.Email)\n    return err\n}\n\ntype UserQueryService struct {\n    readDB *sql.DB\n}\n\nfunc (s *UserQueryService) GetUser(id string) (*User, error) {\n    row := s.readDB.QueryRow(\"SELECT * FROM users WHERE id=$1\", id)\n    u := &User{}\n    return u, row.Scan(&u.ID, &u.Name, &u.Email)\n}',
  notes: 'Separate write handlers from read services. Different DB connections for scaling.',
  idioms: 'Interface for command handling. Struct methods for queries.',
  caveats: 'Type assertion on cmd interface. Consider generics in Go 1.18+ for type-safe commands.'
})-[:FOR_LANGUAGE]->(l);

// --- Adapter ---
MATCH (p:Pattern {name: 'Adapter'}), (l:Language {name: 'python'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'class LegacyPrinter:\n    def print_old(self, text: str) -> str:\n        return f\"[LEGACY] {text}\"\n\nclass ModernPrinter:\n    def print(self, text: str) -> str:\n        return f\"[MODERN] {text}\"\n\nclass PrinterAdapter(ModernPrinter):\n    def __init__(self, legacy: LegacyPrinter):\n        self._legacy = legacy\n    def print(self, text: str) -> str:\n        return self._legacy.print_old(text)',
  notes: 'Wraps legacy interface to match the expected modern interface.',
  idioms: 'Composition-based adapter is preferred over inheritance-based in Python.',
  caveats: 'Only adapts the interface, does not change behavior. Avoid adapting too many methods.'
})-[:FOR_LANGUAGE]->(l);

MATCH (p:Pattern {name: 'Adapter'}), (l:Language {name: 'go'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: 'type Printer interface {\n    Print(text string) string\n}\n\ntype LegacyPrinter struct{}\nfunc (l *LegacyPrinter) PrintOld(text string) string {\n    return \"[LEGACY] \" + text\n}\n\ntype PrinterAdapter struct {\n    legacy *LegacyPrinter\n}\nfunc (a *PrinterAdapter) Print(text string) string {\n    return a.legacy.PrintOld(text)\n}',
  notes: 'Adapter struct wraps legacy and satisfies the modern interface.',
  idioms: 'Implicit interface satisfaction. Embedding for delegation.',
  caveats: 'Go interfaces are satisfied implicitly, so adapters are only needed for name mismatches.'
})-[:FOR_LANGUAGE]->(l);

// --- Hexagonal Architecture ---
MATCH (p:Pattern {name: 'Hexagonal Architecture'}), (l:Language {name: 'python'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: '# Port (interface)\nfrom abc import ABC, abstractmethod\n\nclass UserPort(ABC):\n    @abstractmethod\n    def save(self, user: dict) -> None: ...\n    @abstractmethod\n    def find(self, user_id: str) -> dict: ...\n\n# Domain service (core)\nclass UserService:\n    def __init__(self, repo: UserPort):\n        self._repo = repo\n    def register(self, name: str, email: str) -> dict:\n        user = {\"name\": name, \"email\": email}\n        self._repo.save(user)\n        return user\n\n# Adapter (infrastructure)\nclass PostgresUserAdapter(UserPort):\n    def __init__(self, conn):\n        self._conn = conn\n    def save(self, user: dict) -> None:\n        self._conn.execute(\"INSERT INTO users ...\")\n    def find(self, user_id: str) -> dict:\n        return self._conn.execute(\"SELECT ...\").fetchone()',
  notes: 'Port = ABC interface. Core depends only on ports. Adapters implement ports for specific tech.',
  idioms: 'ABC ports, dataclass domain objects, adapter classes per infrastructure concern.',
  caveats: 'Overhead is significant for small apps. Justified for long-lived systems with evolving infrastructure.'
})-[:FOR_LANGUAGE]->(l);

MATCH (p:Pattern {name: 'Hexagonal Architecture'}), (l:Language {name: 'go'})
CREATE (p)-[:HAS_IMPLEMENTATION]->(i:Implementation {
  code_template: '// Port\ntype UserRepository interface {\n    Save(user *User) error\n    Find(id string) (*User, error)\n}\n\n// Domain\ntype UserService struct {\n    repo UserRepository\n}\nfunc (s *UserService) Register(name, email string) (*User, error) {\n    u := &User{Name: name, Email: email}\n    return u, s.repo.Save(u)\n}\n\n// Adapter\ntype PostgresAdapter struct {\n    db *sql.DB\n}\nfunc (a *PostgresAdapter) Save(user *User) error {\n    _, err := a.db.Exec(\"INSERT INTO users ...\", user.Name)\n    return err\n}',
  notes: 'Go interfaces as ports. Core package depends only on interfaces. Adapters in separate packages.',
  idioms: 'Interface in domain package. Adapter structs in infrastructure package.',
  caveats: 'Package layout is critical. Domain must not import infrastructure packages.'
})-[:FOR_LANGUAGE]->(l);

// =============================================================================
// SEED COMPLETE
// =============================================================================
