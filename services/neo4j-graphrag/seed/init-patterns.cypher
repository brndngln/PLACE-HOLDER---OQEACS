// =============================================================================
// Neo4j Design Pattern Knowledge Graph - Complete Seed Script
// Omni Quantum Elite AI Coding System
// =============================================================================
// 54 patterns across 10 categories, 8 codebases, 8 anti-patterns
// Run with: cypher-shell -f init-patterns.cypher
// =============================================================================

// -----------------------------------------------------------------------------
// 1. CONSTRAINTS & INDEXES
// -----------------------------------------------------------------------------

CREATE CONSTRAINT pattern_name IF NOT EXISTS FOR (p:Pattern) REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT category_name IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT language_name IF NOT EXISTS FOR (l:Language) REQUIRE l.name IS UNIQUE;
CREATE CONSTRAINT codebase_name IF NOT EXISTS FOR (cb:Codebase) REQUIRE cb.name IS UNIQUE;
CREATE CONSTRAINT antipattern_name IF NOT EXISTS FOR (a:AntiPattern) REQUIRE a.name IS UNIQUE;
CREATE INDEX pattern_complexity IF NOT EXISTS FOR (p:Pattern) ON (p.complexity);
CREATE INDEX pattern_category IF NOT EXISTS FOR (p:Pattern) ON (p.category_name);
CREATE FULLTEXT INDEX pattern_search IF NOT EXISTS FOR (p:Pattern) ON EACH [p.name, p.description, p.when_to_use];

// -----------------------------------------------------------------------------
// 2. CATEGORIES (10)
// -----------------------------------------------------------------------------

CREATE (:Category {name: 'Creational', description: 'Patterns that deal with object creation mechanisms, creating objects in a manner suitable to the situation.'});
CREATE (:Category {name: 'Structural', description: 'Patterns that ease design by identifying simple ways to realize relationships among entities.'});
CREATE (:Category {name: 'Behavioral', description: 'Patterns that identify common communication patterns among objects and realize these patterns.'});
CREATE (:Category {name: 'Concurrency', description: 'Patterns that deal with multi-threaded programming paradigms and safe concurrent access.'});
CREATE (:Category {name: 'Resilience', description: 'Patterns that help systems recover from failures and continue operating under adverse conditions.'});
CREATE (:Category {name: 'Data', description: 'Patterns for data access, persistence, and management in application architectures.'});
CREATE (:Category {name: 'API', description: 'Patterns for designing, exposing, and consuming application programming interfaces.'});
CREATE (:Category {name: 'Messaging', description: 'Patterns for asynchronous communication, event-driven architectures, and message-based integration.'});
CREATE (:Category {name: 'Caching', description: 'Patterns for storing and managing frequently accessed data to improve performance.'});
CREATE (:Category {name: 'Security', description: 'Patterns for authentication, authorization, and protecting applications from threats.'});

// -----------------------------------------------------------------------------
// 3. LANGUAGES (6)
// -----------------------------------------------------------------------------

CREATE (:Language {name: 'Python'});
CREATE (:Language {name: 'TypeScript'});
CREATE (:Language {name: 'Go'});
CREATE (:Language {name: 'Rust'});
CREATE (:Language {name: 'C'});
CREATE (:Language {name: 'Java'});

// -----------------------------------------------------------------------------
// 4. ELITE CODEBASES (8)
// -----------------------------------------------------------------------------

CREATE (:Codebase {name: 'linux-kernel', language: 'C', description: 'Linux OS kernel — the most widely deployed operating system kernel in the world.'});
CREATE (:Codebase {name: 'postgresql', language: 'C', description: 'PostgreSQL relational database — advanced open-source RDBMS with extensibility and SQL compliance.'});
CREATE (:Codebase {name: 'redis', language: 'C', description: 'Redis in-memory data store — high-performance key-value store supporting data structures.'});
CREATE (:Codebase {name: 'sqlite', language: 'C', description: 'SQLite embedded SQL database — the most widely deployed database engine in the world.'});
CREATE (:Codebase {name: 'kubernetes', language: 'Go', description: 'Kubernetes container orchestration — production-grade container scheduling and management.'});
CREATE (:Codebase {name: 'tokio', language: 'Rust', description: 'Tokio async runtime — asynchronous runtime for Rust providing I/O, networking, and scheduling.'});
CREATE (:Codebase {name: 'fastapi', language: 'Python', description: 'FastAPI web framework — modern, high-performance Python web framework based on type hints.'});
CREATE (:Codebase {name: 'sentry', language: 'Python', description: 'Sentry error tracking — application monitoring and error tracking platform.'});

// =============================================================================
// 5. PATTERNS (54 total)
// =============================================================================

// -----------------------------------------------------------------------------
// 5.1 CREATIONAL PATTERNS (8)
// -----------------------------------------------------------------------------

// --- Singleton (with full code templates) ---
CREATE (:Pattern {
  name: 'Singleton',
  category_name: 'Creational',
  complexity: 'simple',
  description: 'Ensures a class has only one instance and provides a global point of access to it. Controls concurrent access to shared resources such as configuration managers or connection pools.',
  when_to_use: 'When exactly one object is needed to coordinate actions across the system, such as configuration managers, connection pools, or logging services.',
  when_not_to_use: 'When global state makes testing difficult, when multiple instances may be needed later, or when it hides dependencies making the system harder to reason about.',
  trade_offs: 'Controlled access to sole instance and reduced namespace pollution vs. difficult to test, hidden dependencies, and violates SRP if overloaded.',
  implementation_notes: 'Use thread-safe initialization. Python: __new__ + threading.Lock double-check. Go: sync.Once. Rust: once_cell::Lazy<Mutex<T>>. Prefer DI over Singleton where possible.',
  code_template_python: 'import threading\n\nclass Singleton:\n    _instance = None\n    _lock = threading.Lock()\n\n    def __new__(cls, *args, **kwargs):\n        if cls._instance is None:\n            with cls._lock:\n                if cls._instance is None:\n                    cls._instance = super().__new__(cls)\n        return cls._instance\n\n    def __init__(self):\n        if not hasattr(self, \"_initialized\"):\n            self._initialized = True',
  code_template_go: 'package singleton\n\nimport \"sync\"\n\ntype singleton struct {\n    Value string\n}\n\nvar (\n    instance *singleton\n    once     sync.Once\n)\n\nfunc GetInstance() *singleton {\n    once.Do(func() {\n        instance = &singleton{Value: \"initialized\"}\n    })\n    return instance\n}',
  code_template_rust: 'use once_cell::sync::Lazy;\nuse std::sync::Mutex;\n\nstruct Singleton {\n    value: String,\n}\n\nstatic INSTANCE: Lazy<Mutex<Singleton>> = Lazy::new(|| {\n    Mutex::new(Singleton {\n        value: String::from(\"initialized\"),\n    })\n});\n\npub fn get_instance() -> &''static Mutex<Singleton> {\n    &INSTANCE\n}',
  test_template: 'import threading\n\ndef test_singleton_same_instance():\n    a = Singleton()\n    b = Singleton()\n    assert a is b\n\ndef test_singleton_thread_safety():\n    instances = []\n    def create():\n        instances.append(Singleton())\n    threads = [threading.Thread(target=create) for _ in range(100)]\n    for t in threads:\n        t.start()\n    for t in threads:\n        t.join()\n    assert all(i is instances[0] for i in instances)'
});

// --- Factory Method (with full code templates) ---
CREATE (:Pattern {
  name: 'Factory Method',
  category_name: 'Creational',
  complexity: 'moderate',
  description: 'Defines an interface for creating an object but lets subclasses or registry decide which class to instantiate. Defers instantiation logic to a central factory with pluggable product types.',
  when_to_use: 'When a class cannot anticipate the type of objects it needs to create, when subclasses should specify the objects they create, or when creation logic is complex and should be centralized.',
  when_not_to_use: 'When the creation logic is trivial and unlikely to change, adding unnecessary abstraction layers.',
  trade_offs: 'Eliminates tight coupling to concrete classes and supports open/closed principle vs. requires additional class hierarchy and can lead to parallel hierarchies.',
  implementation_notes: 'Python: ABC + registry dict + register(). Go: switch-based constructor. Include validation for unknown product types.',
  code_template_python: 'from abc import ABC, abstractmethod\nfrom typing import Dict, Type\n\nclass Product(ABC):\n    @abstractmethod\n    def operation(self) -> str: ...\n\nclass ConcreteProductA(Product):\n    def operation(self) -> str:\n        return \"Result of ConcreteProductA\"\n\nclass ConcreteProductB(Product):\n    def operation(self) -> str:\n        return \"Result of ConcreteProductB\"\n\nclass ProductFactory:\n    _registry: Dict[str, Type[Product]] = {}\n\n    @classmethod\n    def register(cls, name: str, product_cls: Type[Product]) -> None:\n        cls._registry[name] = product_cls\n\n    @classmethod\n    def create(cls, name: str) -> Product:\n        if name not in cls._registry:\n            raise ValueError(f\"Unknown product: {name}\")\n        return cls._registry[name]()\n\nProductFactory.register(\"a\", ConcreteProductA)\nProductFactory.register(\"b\", ConcreteProductB)',
  code_template_go: 'package factory\n\ntype Product interface {\n    Operation() string\n}\n\ntype ConcreteProductA struct{}\nfunc (p *ConcreteProductA) Operation() string { return \"Result of ConcreteProductA\" }\n\ntype ConcreteProductB struct{}\nfunc (p *ConcreteProductB) Operation() string { return \"Result of ConcreteProductB\" }\n\nfunc NewProduct(name string) Product {\n    switch name {\n    case \"a\":\n        return &ConcreteProductA{}\n    case \"b\":\n        return &ConcreteProductB{}\n    default:\n        return nil\n    }\n}',
  test_template: 'def test_factory_creates_correct_type():\n    a = ProductFactory.create(\"a\")\n    assert isinstance(a, ConcreteProductA)\n    assert a.operation() == \"Result of ConcreteProductA\"\n\ndef test_factory_register_new():\n    class Custom(Product):\n        def operation(self) -> str:\n            return \"custom\"\n    ProductFactory.register(\"custom\", Custom)\n    assert ProductFactory.create(\"custom\").operation() == \"custom\"\n\ndef test_factory_unknown_raises():\n    import pytest\n    with pytest.raises(ValueError):\n        ProductFactory.create(\"unknown\")'
});

// --- Builder ---
CREATE (:Pattern {
  name: 'Builder',
  category_name: 'Creational',
  complexity: 'moderate',
  description: 'Separates the construction of a complex object from its representation, allowing the same construction process to create different representations via a fluent step-by-step API.',
  when_to_use: 'When an object requires many optional parameters, when construction involves multiple steps, or when you want immutable objects built incrementally.',
  when_not_to_use: 'When objects are simple with few parameters, or when the construction process does not vary.',
  trade_offs: 'Readable construction of complex objects and immutability support vs. requires separate builder class per product and verbose for simple objects.',
  implementation_notes: 'Return self for method chaining. Separate build() method for validation. Consider frozen dataclass for the result object.'
});

// --- Abstract Factory ---
CREATE (:Pattern {
  name: 'Abstract Factory',
  category_name: 'Creational',
  complexity: 'complex',
  description: 'Provides an interface for creating families of related or dependent objects without specifying their concrete classes. Ensures product compatibility within a family.',
  when_to_use: 'When a system must be independent of how its products are created, or when a system should work with multiple families of products that must be used together.',
  when_not_to_use: 'When there is only one family of products or when adding new product types requires changing the abstract interface.',
  trade_offs: 'Ensures consistent product families and isolates concrete classes vs. difficult to add new product types and increases class count.',
  implementation_notes: 'Define abstract factory interface with create methods for each product. Concrete factories produce compatible product families.'
});

// --- Prototype ---
CREATE (:Pattern {
  name: 'Prototype',
  category_name: 'Creational',
  complexity: 'moderate',
  description: 'Creates new objects by copying an existing object (prototype) rather than creating from scratch. Useful when object creation is expensive and similar objects are frequently needed.',
  when_to_use: 'When object creation is expensive and similar objects are frequently needed, or when classes to instantiate are specified at runtime.',
  when_not_to_use: 'When objects have complex circular references that make deep copying difficult, or when creation cost is negligible.',
  trade_offs: 'Avoids costly initialization by cloning pre-built prototypes vs. deep copying complex object graphs can be tricky and error-prone.',
  implementation_notes: 'Python: copy.deepcopy(). Go: implement Clone() method. Rust: derive Clone trait. Be careful with deep vs shallow copy semantics.'
});

// --- Object Pool ---
CREATE (:Pattern {
  name: 'Object Pool',
  category_name: 'Creational',
  complexity: 'moderate',
  description: 'Manages a pool of reusable objects to avoid the overhead of creating and destroying objects repeatedly. Objects are checked out, used, and returned to the pool.',
  when_to_use: 'When object creation is expensive (database connections, threads, large buffers) and objects are needed frequently but briefly.',
  when_not_to_use: 'When object creation is cheap, when objects hold state that is difficult to reset, or when pool management overhead exceeds creation cost.',
  trade_offs: 'Reduced creation overhead and predictable resource usage vs. complexity of pool management, potential for resource leaks if objects are not returned.',
  implementation_notes: 'Track active vs idle objects. Implement checkout/return with cleanup. Set min/max pool size. Add health checks and eviction for stale objects.'
});

// --- Dependency Injection ---
CREATE (:Pattern {
  name: 'Dependency Injection',
  category_name: 'Creational',
  complexity: 'simple',
  description: 'A technique where an object receives its dependencies from external sources rather than creating them internally. Promotes loose coupling and testability.',
  when_to_use: 'When classes should be testable in isolation, when dependencies may change, when following SOLID principles especially Dependency Inversion.',
  when_not_to_use: 'When the application is trivially simple and injection adds unnecessary complexity, or when dependencies are truly fixed and internal.',
  trade_offs: 'Loose coupling, testability, and explicit dependencies vs. can obscure control flow and requires wiring infrastructure.',
  implementation_notes: 'Constructor injection is preferred. Python: FastAPI Depends(). Go: pass interfaces to constructors. Avoid service locator as a substitute.'
});

// --- Registry ---
CREATE (:Pattern {
  name: 'Registry',
  category_name: 'Creational',
  complexity: 'simple',
  description: 'A well-known object that other objects use to find common objects and services. Acts as a global lookup table mapping names or keys to object instances.',
  when_to_use: 'When multiple parts of a system need to locate shared services or implementations by name, plugin architectures, strategy resolution.',
  when_not_to_use: 'When dependency injection provides cleaner explicit wiring, or when the registry becomes a god object hiding dependencies.',
  trade_offs: 'Centralized service lookup and dynamic registration vs. hidden dependencies similar to service locator, harder to test.',
  implementation_notes: 'Use a dict mapping names to factories or instances. Support register() and get() operations. Consider thread safety for concurrent access.'
});

// -----------------------------------------------------------------------------
// 5.2 STRUCTURAL PATTERNS (7)
// -----------------------------------------------------------------------------

// --- Adapter ---
CREATE (:Pattern {
  name: 'Adapter',
  category_name: 'Structural',
  complexity: 'simple',
  description: 'Converts the interface of a class into another interface clients expect. Lets classes work together that could not otherwise due to incompatible interfaces.',
  when_to_use: 'When integrating legacy code with new systems, wrapping third-party libraries, or when existing classes have incompatible interfaces.',
  when_not_to_use: 'When the interfaces are already compatible, or when a redesign of the interface would be more appropriate.',
  trade_offs: 'Enables integration of incompatible interfaces without modifying source vs. adds a layer of indirection and can accumulate technical debt.',
  implementation_notes: 'Prefer composition-based adapter over inheritance-based. Implement the target interface and delegate to the adaptee.'
});

// --- Facade ---
CREATE (:Pattern {
  name: 'Facade',
  category_name: 'Structural',
  complexity: 'simple',
  description: 'Provides a unified interface to a set of interfaces in a subsystem. Defines a higher-level interface that makes the subsystem easier to use.',
  when_to_use: 'When providing a simple interface to a complex subsystem, when decoupling clients from subsystem components, or when layering a system.',
  when_not_to_use: 'When the facade becomes a god object that couples to everything, or when clients need fine-grained access to subsystem features.',
  trade_offs: 'Simplified interface and reduced client coupling to subsystem vs. can become a god object if not bounded and hides useful complexity.',
  implementation_notes: 'Keep the facade thin. Delegate to subsystem components. Do not add business logic to the facade itself.'
});

// --- Decorator ---
CREATE (:Pattern {
  name: 'Decorator',
  category_name: 'Structural',
  complexity: 'moderate',
  description: 'Attaches additional responsibilities to an object dynamically. Provides a flexible alternative to subclassing for extending functionality.',
  when_to_use: 'When adding responsibilities to individual objects without affecting others, when extension by subclassing is impractical due to combinatorial explosion.',
  when_not_to_use: 'When the order of decoration matters and is hard to control, or when many small decorators create complexity in debugging.',
  trade_offs: 'Dynamic behavior addition and avoids subclass explosion vs. many small objects, decorator ordering matters, and debugging complexity.',
  implementation_notes: 'Python decorators are the language-native implementation. Use functools.wraps to preserve metadata. Stack decorators for composed behavior.'
});

// --- Proxy ---
CREATE (:Pattern {
  name: 'Proxy',
  category_name: 'Structural',
  complexity: 'moderate',
  description: 'Provides a surrogate or placeholder for another object to control access to it. Types include virtual (lazy init), protection (access control), and remote (network) proxies.',
  when_to_use: 'When lazy initialization, access control, logging, or caching is needed around an object without changing its interface.',
  when_not_to_use: 'When the indirection adds latency without benefit, or when the original object is simple and always available.',
  trade_offs: 'Transparent interception for cross-cutting concerns vs. adds indirection and latency, can be confusing when debugging.',
  implementation_notes: 'Implement the same interface as the real subject. Delegate to the real subject after performing proxy logic.'
});

// --- Composite ---
CREATE (:Pattern {
  name: 'Composite',
  category_name: 'Structural',
  complexity: 'moderate',
  description: 'Composes objects into tree structures to represent part-whole hierarchies. Lets clients treat individual objects and compositions uniformly.',
  when_to_use: 'When representing part-whole hierarchies, when clients should treat composite and individual objects uniformly, such as file systems or UI components.',
  when_not_to_use: 'When the tree structure is not natural, or when leaf and composite objects need very different interfaces.',
  trade_offs: 'Uniform treatment of individual and composite objects vs. can make design overly general and type safety harder to enforce.',
  implementation_notes: 'Define a component interface. Leaf nodes implement operations directly. Composite nodes delegate to children and aggregate results.'
});

// --- Bridge ---
CREATE (:Pattern {
  name: 'Bridge',
  category_name: 'Structural',
  complexity: 'complex',
  description: 'Decouples an abstraction from its implementation so that the two can vary independently. Useful when both dimensions of a design need to evolve separately.',
  when_to_use: 'When both the abstraction and implementation need to be extended independently, or when implementation changes should not affect client code.',
  when_not_to_use: 'When the abstraction has only one possible implementation, or when the complexity of separation is not justified.',
  trade_offs: 'Independent evolution of abstraction and implementation vs. increased complexity from additional indirection layers.',
  implementation_notes: 'Abstraction holds a reference to the implementation interface. Both can have their own class hierarchies that evolve independently.'
});

// --- Flyweight ---
CREATE (:Pattern {
  name: 'Flyweight',
  category_name: 'Structural',
  complexity: 'complex',
  description: 'Uses sharing to support large numbers of fine-grained objects efficiently. Separates intrinsic (shared) state from extrinsic (context-specific) state.',
  when_to_use: 'When an application uses a large number of objects that share common state, when memory optimization is critical.',
  when_not_to_use: 'When objects do not share significant state, or when the overhead of separating intrinsic and extrinsic state exceeds the memory savings.',
  trade_offs: 'Significant memory reduction for large object counts vs. added complexity of state separation and potential threading issues with shared state.',
  implementation_notes: 'Use a factory that caches and returns shared instances. Intrinsic state is stored in the flyweight; extrinsic state is passed by the client.'
});

// -----------------------------------------------------------------------------
// 5.3 BEHAVIORAL PATTERNS (8)
// -----------------------------------------------------------------------------

// --- Observer ---
CREATE (:Pattern {
  name: 'Observer',
  category_name: 'Behavioral',
  complexity: 'moderate',
  description: 'Defines a one-to-many dependency between objects so that when one object changes state, all its dependents are notified and updated automatically.',
  when_to_use: 'When changes to one object require changing others and you do not know how many objects need to change, event-driven architectures, UI data binding.',
  when_not_to_use: 'When the notification order matters and is hard to guarantee, or when cascading updates could cause performance issues.',
  trade_offs: 'Loose coupling between subject and observers and dynamic subscription vs. unexpected updates, memory leaks from forgotten subscriptions.',
  implementation_notes: 'Use callback lists or event emitters. Consider weakref to prevent memory leaks. Implement unsubscribe for cleanup.'
});

// --- Strategy ---
CREATE (:Pattern {
  name: 'Strategy',
  category_name: 'Behavioral',
  complexity: 'simple',
  description: 'Defines a family of algorithms, encapsulates each one, and makes them interchangeable. Lets the algorithm vary independently from clients that use it.',
  when_to_use: 'When you need different variants of an algorithm, when a class has multiple conditional behaviors, or when you want to isolate algorithm logic.',
  when_not_to_use: 'When there are only two simple alternatives that rarely change and a conditional is clearer.',
  trade_offs: 'Runtime algorithm switching and eliminates conditionals vs. clients must be aware of different strategies and increases number of objects.',
  implementation_notes: 'Python: Protocol for structural typing or plain callables. Go: interfaces. Rust: trait objects or generics.'
});

// --- Command ---
CREATE (:Pattern {
  name: 'Command',
  category_name: 'Behavioral',
  complexity: 'moderate',
  description: 'Encapsulates a request as an object, letting you parameterize clients with different requests, queue or log requests, and support undoable operations.',
  when_to_use: 'When implementing undo/redo, task queues, macro recording, transactional behavior, or when requests need to be serialized.',
  when_not_to_use: 'When requests are simple one-off operations that do not need queuing, logging, or undo support.',
  trade_offs: 'Decouples invoker from executor and enables undo and queuing vs. increased number of classes and overhead for simple operations.',
  implementation_notes: 'Define execute() and undo() methods. Use a command history stack for undo. Commands can be composed into macros.'
});

// --- Chain of Responsibility ---
CREATE (:Pattern {
  name: 'Chain of Responsibility',
  category_name: 'Behavioral',
  complexity: 'moderate',
  description: 'Avoids coupling the sender of a request to its receiver by giving more than one object a chance to handle it. Chains the receiving objects and passes the request along.',
  when_to_use: 'When multiple objects may handle a request and the handler is not known a priori, middleware pipelines, validation chains, logging pipelines.',
  when_not_to_use: 'When requests must always be handled and dropping them is unacceptable without guaranteed termination.',
  trade_offs: 'Decoupled request handling and flexible chain configuration vs. no guarantee of handling and debugging can be difficult.',
  implementation_notes: 'Each handler has a reference to the next handler. Process or pass along. Use in middleware stacks (FastAPI, Express, Go HTTP middleware).'
});

// --- State Machine ---
CREATE (:Pattern {
  name: 'State Machine',
  category_name: 'Behavioral',
  complexity: 'moderate',
  description: 'Allows an object to alter its behavior when its internal state changes. The object appears to change its class. Formalizes state transitions and guards.',
  when_to_use: 'When object behavior depends on its state and must change at runtime, when state-specific code is scattered across many conditionals, protocol implementations.',
  when_not_to_use: 'When there are only two or three simple states, or when state transitions are trivial and a boolean flag suffices.',
  trade_offs: 'Organizes state-dependent behavior and makes transitions explicit vs. can lead to many state classes and complex transition logic.',
  implementation_notes: 'Define state interface with methods for each action. Each concrete state implements transitions. Context delegates to current state object.'
});

// --- Iterator ---
CREATE (:Pattern {
  name: 'Iterator',
  category_name: 'Behavioral',
  complexity: 'simple',
  description: 'Provides a way to access the elements of an aggregate object sequentially without exposing its underlying representation.',
  when_to_use: 'When you need to traverse complex data structures without exposing their internals, when multiple traversal algorithms are needed.',
  when_not_to_use: 'When the collection is simple and direct access is sufficient, or when the language provides adequate built-in iteration.',
  trade_offs: 'Encapsulates traversal logic and supports multiple concurrent iterations vs. can be overkill for simple collections.',
  implementation_notes: 'Python: __iter__ and __next__ protocol. Go: channels or callback functions. Rust: Iterator trait. Most languages have built-in support.'
});

// --- Template Method ---
CREATE (:Pattern {
  name: 'Template Method',
  category_name: 'Behavioral',
  complexity: 'simple',
  description: 'Defines the skeleton of an algorithm in a method, deferring some steps to subclasses without changing the overall algorithm structure.',
  when_to_use: 'When multiple classes share the same algorithm structure but differ in specific steps, when you want to let subclasses extend specific parts of an algorithm.',
  when_not_to_use: 'When the algorithm has no invariant steps, or when composition via Strategy is more flexible and preferred.',
  trade_offs: 'Code reuse for shared algorithm skeleton and controlled extension points vs. relies on inheritance which limits flexibility.',
  implementation_notes: 'Define the template method as final/non-overridable. Use abstract methods for steps that vary. Hook methods provide optional extension points.'
});

// --- Visitor ---
CREATE (:Pattern {
  name: 'Visitor',
  category_name: 'Behavioral',
  complexity: 'complex',
  description: 'Represents an operation to be performed on elements of an object structure. Lets you define new operations without changing the classes of the elements.',
  when_to_use: 'When you need to perform many distinct operations on a complex object structure, when the structure is stable but operations change frequently.',
  when_not_to_use: 'When the object structure changes frequently, as every new element type requires updating all visitors.',
  trade_offs: 'Easy to add new operations without modifying element classes vs. difficult to add new element types and breaks encapsulation.',
  implementation_notes: 'Implement accept(visitor) on elements. Visitor has visit methods for each element type. Use double dispatch for type resolution.'
});

// -----------------------------------------------------------------------------
// 5.4 CONCURRENCY PATTERNS (6)
// -----------------------------------------------------------------------------

// --- Producer-Consumer ---
CREATE (:Pattern {
  name: 'Producer-Consumer',
  category_name: 'Concurrency',
  complexity: 'moderate',
  description: 'Decouples components that produce data from those that consume it using a shared buffer or queue for asynchronous processing.',
  when_to_use: 'When producers and consumers operate at different rates, when buffering work for async processing, when decoupling processing stages.',
  when_not_to_use: 'When synchronous processing is required, or when the overhead of queue management exceeds the benefit.',
  trade_offs: 'Decoupled throughput, buffered processing, and rate smoothing vs. queue management overhead, potential memory issues, and ordering complexity.',
  implementation_notes: 'Python: asyncio.Queue or queue.Queue. Go: buffered channels. Use sentinel values or context cancellation for shutdown.'
});

// --- Thread Pool ---
CREATE (:Pattern {
  name: 'Thread Pool',
  category_name: 'Concurrency',
  complexity: 'moderate',
  description: 'Manages a pool of reusable threads to execute tasks, reducing the overhead of thread creation and destruction for many short-lived tasks.',
  when_to_use: 'When many short-lived tasks need concurrent execution, when thread creation overhead is significant, web server request handling.',
  when_not_to_use: 'When tasks are long-running and block threads indefinitely, or when async IO is more appropriate.',
  trade_offs: 'Reduced thread creation overhead and bounded resource usage vs. potential for thread starvation and deadlocks if tasks block.',
  implementation_notes: 'Python: concurrent.futures.ThreadPoolExecutor. Go: goroutine pools with semaphore. Set pool size based on workload type (CPU-bound vs IO-bound).'
});

// --- Read-Write Lock ---
CREATE (:Pattern {
  name: 'Read-Write Lock',
  category_name: 'Concurrency',
  complexity: 'moderate',
  description: 'Allows concurrent read access to a shared resource while ensuring exclusive access for writes, improving throughput in read-heavy scenarios.',
  when_to_use: 'When reads vastly outnumber writes and concurrent read access improves performance, shared configuration, caches.',
  when_not_to_use: 'When writes are frequent and readers would starve, or when a simpler mutex suffices for the access pattern.',
  trade_offs: 'Improved read throughput in read-heavy workloads vs. write starvation risk, more complex than a simple mutex, potential for priority inversion.',
  implementation_notes: 'Python: threading.RLock or asyncio.Lock. Go: sync.RWMutex. Rust: std::sync::RwLock. Consider reader-writer fairness policies.'
});

// --- Actor Model ---
CREATE (:Pattern {
  name: 'Actor Model',
  category_name: 'Concurrency',
  complexity: 'complex',
  description: 'Concurrent computation model where actors are independent units that communicate exclusively through asynchronous message passing. No shared mutable state.',
  when_to_use: 'When building highly concurrent systems, when shared mutable state must be avoided, in distributed systems requiring fault isolation.',
  when_not_to_use: 'When synchronous request-response is simpler, when the overhead of message passing is not justified for the concurrency level.',
  trade_offs: 'No shared state, natural distribution, and fault isolation vs. message passing overhead, debugging difficulty, and potential mailbox overflow.',
  implementation_notes: 'Each actor has a mailbox, processes one message at a time. Erlang/Elixir have native support. Python: use asyncio tasks with queues. Rust: actix or tokio channels.'
});

// --- Semaphore ---
CREATE (:Pattern {
  name: 'Semaphore',
  category_name: 'Concurrency',
  complexity: 'simple',
  description: 'Controls access to a shared resource by maintaining a counter of available permits. Threads acquire permits before accessing the resource and release them when done.',
  when_to_use: 'When limiting concurrent access to a resource pool, connection limiting, rate throttling at the thread level.',
  when_not_to_use: 'When a simple mutex (binary semaphore) suffices, or when higher-level patterns like thread pools handle concurrency.',
  trade_offs: 'Simple bounded concurrency control vs. potential for deadlocks if permits are not properly released, no ownership tracking.',
  implementation_notes: 'Python: asyncio.Semaphore or threading.Semaphore. Go: channel-based semaphore (buffered channel of struct{}). Always release in finally/defer.'
});

// --- Future/Promise ---
CREATE (:Pattern {
  name: 'Future/Promise',
  category_name: 'Concurrency',
  complexity: 'simple',
  description: 'Represents a value that will be available in the future, allowing asynchronous computation to be composed and chained without blocking.',
  when_to_use: 'When coordinating asynchronous operations, when composing non-blocking workflows, when parallelizing independent tasks.',
  when_not_to_use: 'When synchronous execution is simpler and performance is acceptable, or when the operation is inherently sequential.',
  trade_offs: 'Composable async workflows and concurrent execution of independent tasks vs. error handling complexity and potential for unhandled rejections.',
  implementation_notes: 'Python: asyncio.Task + gather(). Go: goroutines + channels or errgroup. Rust: tokio::join! macro. Handle errors at await points.'
});

// -----------------------------------------------------------------------------
// 5.5 RESILIENCE PATTERNS (6)
// -----------------------------------------------------------------------------

// --- Circuit Breaker ---
CREATE (:Pattern {
  name: 'Circuit Breaker',
  category_name: 'Resilience',
  complexity: 'moderate',
  description: 'Prevents an application from repeatedly trying an operation that is likely to fail, allowing it to recover gracefully. Transitions through CLOSED, OPEN, and HALF_OPEN states.',
  when_to_use: 'When calling external services that may fail, in microservice architectures to prevent cascade failures, when fail-fast behavior is needed.',
  when_not_to_use: 'When calling local in-process operations that cannot fail independently, or when retries are always safe.',
  trade_offs: 'Prevents cascade failures and enables graceful degradation vs. adds latency for health checks and requires careful threshold tuning.',
  implementation_notes: 'States: CLOSED (normal) -> OPEN (failing fast) -> HALF_OPEN (testing recovery). Track failure count and rate. Configure failure threshold, timeout, and half-open trial count.'
});

// --- Retry with Backoff ---
CREATE (:Pattern {
  name: 'Retry with Backoff',
  category_name: 'Resilience',
  complexity: 'simple',
  description: 'Automatically retries failed operations with increasing delays between attempts. Adds jitter to prevent thundering herd on recovery.',
  when_to_use: 'When transient failures are expected (network timeouts, rate limits, temporary unavailability) and the operation is idempotent.',
  when_not_to_use: 'When failures are permanent (bad request, auth failure), when the operation is not idempotent, or when immediate failure feedback is needed.',
  trade_offs: 'Transparent recovery from transient failures vs. increased latency on failure and potential for resource exhaustion if not bounded.',
  implementation_notes: 'Formula: delay = base * 2^attempt + jitter. Use tenacity in Python, backoff libraries. Set max_attempts and max_delay. Always add jitter to prevent thundering herd.'
});

// --- Bulkhead ---
CREATE (:Pattern {
  name: 'Bulkhead',
  category_name: 'Resilience',
  complexity: 'moderate',
  description: 'Isolates elements of an application into pools so that if one fails, the others continue to function. Named after ship bulkheads that prevent flooding.',
  when_to_use: 'When a failure in one component should not affect others, when resources need to be partitioned for fault isolation.',
  when_not_to_use: 'When the system is simple enough that isolation adds unnecessary complexity, or when all components share the same failure mode.',
  trade_offs: 'Fault isolation prevents cascade failures and maintains partial functionality vs. resource underutilization from static partitioning.',
  implementation_notes: 'Use separate thread pools, connection pools, or process pools for different concerns. Combine with circuit breaker for comprehensive resilience.'
});

// --- Timeout ---
CREATE (:Pattern {
  name: 'Timeout',
  category_name: 'Resilience',
  complexity: 'simple',
  description: 'Sets a maximum time limit for an operation to complete. If the operation exceeds the timeout, it is aborted to prevent indefinite blocking.',
  when_to_use: 'For all external calls (HTTP, database, RPC), when operations could potentially hang or take unreasonably long.',
  when_not_to_use: 'When operations are guaranteed to complete quickly, or when long-running operations have their own progress reporting.',
  trade_offs: 'Prevents indefinite blocking and resource exhaustion vs. may prematurely cancel operations that would have succeeded, needs careful tuning.',
  implementation_notes: 'Python: asyncio.wait_for() or httpx timeout. Go: context.WithTimeout(). Always set timeouts on external calls. Log timeout events for tuning.'
});

// --- Fallback ---
CREATE (:Pattern {
  name: 'Fallback',
  category_name: 'Resilience',
  complexity: 'simple',
  description: 'Provides an alternative action or default response when the primary operation fails. Enables graceful degradation rather than hard failure.',
  when_to_use: 'When a degraded response is better than no response, when cached data can serve as a fallback, when there are alternative service providers.',
  when_not_to_use: 'When the fallback could produce incorrect results that are worse than an error, or when there is no meaningful alternative.',
  trade_offs: 'Continued service under failure conditions vs. potentially stale or incomplete responses, complexity of maintaining fallback logic.',
  implementation_notes: 'Common strategies: return cached data, use a default value, call an alternative service, return a simplified response. Combine with circuit breaker.'
});

// --- Health Check ---
CREATE (:Pattern {
  name: 'Health Check',
  category_name: 'Resilience',
  complexity: 'simple',
  description: 'Exposes endpoints that report the operational status of a service and its dependencies. Enables load balancers and orchestrators to route traffic appropriately.',
  when_to_use: 'In every service, always. Required for container orchestration, load balancing, and monitoring.',
  when_not_to_use: 'There is no valid reason to skip health checks in production services.',
  trade_offs: 'Essential for operations and automated recovery vs. health check logic can become stale or fail to detect actual issues.',
  implementation_notes: 'Implement /health (liveness), /ready (readiness), and /metrics (observability). Liveness checks the process; readiness checks dependencies. Keep checks fast and side-effect free.'
});

// -----------------------------------------------------------------------------
// 5.6 DATA PATTERNS (5)
// -----------------------------------------------------------------------------

// --- Repository ---
CREATE (:Pattern {
  name: 'Repository',
  category_name: 'Data',
  complexity: 'simple',
  description: 'Mediates between the domain and data mapping layers using a collection-like interface for accessing domain objects. Abstracts data access behind a clean API.',
  when_to_use: 'When domain logic should be independent of data access details, when testing requires mock data sources, when supporting multiple backends.',
  when_not_to_use: 'When the application is a simple CRUD with no domain logic, adding unnecessary abstraction.',
  trade_offs: 'Testable domain logic, swappable data sources, and clean separation vs. additional abstraction layer that can become leaky.',
  implementation_notes: 'Define interface with get, save, delete, list methods. Concrete implementations encapsulate SQL/ORM/API calls. Use dependency injection to provide implementation.'
});

// --- Unit of Work ---
CREATE (:Pattern {
  name: 'Unit of Work',
  category_name: 'Data',
  complexity: 'complex',
  description: 'Maintains a list of objects affected by a business transaction and coordinates writing out changes and resolving concurrency problems as a single atomic operation.',
  when_to_use: 'When multiple objects must be persisted atomically, when tracking dirty objects for batch writes, when transaction coordination is needed.',
  when_not_to_use: 'When each operation is independent and does not require transactional grouping.',
  trade_offs: 'Atomic persistence of related changes and reduced database round-trips vs. complexity of tracking changes and potential memory overhead.',
  implementation_notes: 'Track new, dirty, and deleted objects. Commit flushes all changes in a single transaction. Rollback discards pending changes. Python: SQLAlchemy Session is a UoW.'
});

// --- CQRS ---
CREATE (:Pattern {
  name: 'CQRS',
  category_name: 'Data',
  complexity: 'complex',
  description: 'Command Query Responsibility Segregation separates read and write operations into different models, optimizing each independently for their specific workload.',
  when_to_use: 'When read and write workloads have different performance or scaling requirements, when complex domain logic applies only to writes.',
  when_not_to_use: 'When read and write models are identical, in simple CRUD applications where the added complexity is not justified.',
  trade_offs: 'Independent scaling of reads and writes and optimized models vs. eventual consistency complexity and data synchronization overhead.',
  implementation_notes: 'Separate command handlers (write) from query services (read). Can use different databases for each side. Sync via events or change data capture.'
});

// --- Event Sourcing ---
CREATE (:Pattern {
  name: 'Event Sourcing',
  category_name: 'Data',
  complexity: 'complex',
  description: 'Stores all changes to application state as a sequence of immutable events rather than storing current state. Events can be replayed to reconstruct any past state.',
  when_to_use: 'When complete audit trails are required, when temporal queries or event replay are needed, when used with CQRS for separate read models.',
  when_not_to_use: 'When eventual consistency is unacceptable, when storage costs of all events are prohibitive, in simple CRUD systems.',
  trade_offs: 'Complete audit trail, temporal queries, and event replay vs. storage growth, eventual consistency, and schema evolution complexity.',
  implementation_notes: 'Store events in an append-only event store. Build read models by replaying events (projections). Use snapshots to optimize replay for long-lived aggregates.'
});

// --- Data Transfer Object ---
CREATE (:Pattern {
  name: 'Data Transfer Object',
  category_name: 'Data',
  complexity: 'simple',
  description: 'An object that carries data between processes to reduce the number of method calls. Contains only data fields with no business logic.',
  when_to_use: 'When transferring data between layers or services, API request/response bodies, when the internal domain model should not be exposed.',
  when_not_to_use: 'When the domain model is simple enough to be used directly, or when DTOs would just mirror domain objects without adding value.',
  trade_offs: 'Clean API contracts and decoupled internal models vs. mapping boilerplate between DTOs and domain objects.',
  implementation_notes: 'Python: Pydantic BaseModel or dataclass. Go: plain structs. TypeScript: interfaces. Keep DTOs focused on the specific use case.'
});

// -----------------------------------------------------------------------------
// 5.7 API PATTERNS (5)
// -----------------------------------------------------------------------------

// --- API Gateway ---
CREATE (:Pattern {
  name: 'API Gateway',
  category_name: 'API',
  complexity: 'moderate',
  description: 'Provides a single entry point for all client requests, routing them to appropriate microservices and handling cross-cutting concerns like auth, rate limiting, and aggregation.',
  when_to_use: 'In microservice architectures to simplify client interactions, when cross-cutting concerns need centralized management.',
  when_not_to_use: 'When a single monolithic backend handles all requests, or when the gateway becomes a performance bottleneck.',
  trade_offs: 'Simplified client interaction and centralized cross-cutting concerns vs. single point of failure and potential bottleneck.',
  implementation_notes: 'Use Traefik, Kong, or custom FastAPI gateway. Implement request routing, auth validation, rate limiting, response aggregation, and protocol translation.'
});

// --- Backend for Frontend ---
CREATE (:Pattern {
  name: 'Backend for Frontend',
  category_name: 'API',
  complexity: 'moderate',
  description: 'Creates separate backend services tailored to the needs of each frontend application (web, mobile, desktop) rather than a one-size-fits-all API.',
  when_to_use: 'When different frontends have significantly different data and interaction needs, when mobile needs differ substantially from web.',
  when_not_to_use: 'When all frontends have similar requirements, or when maintaining multiple BFFs creates too much duplication.',
  trade_offs: 'Optimized APIs per client type and independent evolution vs. code duplication across BFFs and more services to maintain.',
  implementation_notes: 'Each BFF aggregates calls to downstream microservices. Tailor response shapes and batch operations for each client type. Share common logic via libraries.'
});

// --- Pagination ---
CREATE (:Pattern {
  name: 'Pagination',
  category_name: 'API',
  complexity: 'simple',
  description: 'Divides large result sets into discrete pages to limit response size and improve performance. Supports offset-based, cursor-based, and keyset pagination.',
  when_to_use: 'For any API endpoint that can return unbounded results, list endpoints, search results, feeds.',
  when_not_to_use: 'When the total result set is always small and bounded (e.g., enum values, configuration lists).',
  trade_offs: 'Bounded response sizes and predictable performance vs. complexity of pagination logic and potential for inconsistent pages during concurrent writes.',
  implementation_notes: 'Cursor-based pagination is preferred for large datasets (no offset drift). Use LIMIT+1 to detect has_next_page. Return pagination metadata in response.'
});

// --- Idempotency ---
CREATE (:Pattern {
  name: 'Idempotency',
  category_name: 'API',
  complexity: 'moderate',
  description: 'Ensures that making the same request multiple times produces the same result as making it once. Critical for safe retries in distributed systems.',
  when_to_use: 'For all mutation endpoints (POST, PUT, DELETE) in distributed systems, payment processing, message handling.',
  when_not_to_use: 'For read-only (GET) operations which are inherently idempotent, or for operations where duplicates are acceptable.',
  trade_offs: 'Safe retries and reliable distributed operations vs. storage overhead for idempotency keys and complexity of deduplication logic.',
  implementation_notes: 'Accept an Idempotency-Key header. Store request hash and response. Return cached response for duplicate requests. Set TTL for idempotency records.'
});

// --- Rate Limiting ---
CREATE (:Pattern {
  name: 'Rate Limiting',
  category_name: 'API',
  complexity: 'moderate',
  description: 'Controls the rate of requests a client can make to an API within a time window. Protects services from abuse and ensures fair resource allocation.',
  when_to_use: 'When protecting APIs from abuse, ensuring fair usage across clients, preventing resource exhaustion during traffic spikes.',
  when_not_to_use: 'When the API is internal-only with trusted clients and traffic is predictable and well within capacity.',
  trade_offs: 'Protection from abuse and fair resource allocation vs. potential rejection of legitimate traffic and complexity in choosing appropriate limits.',
  implementation_notes: 'Common algorithms: token bucket, sliding window, fixed window. Store counters in Redis for distributed rate limiting. Return 429 status with Retry-After header.'
});

// -----------------------------------------------------------------------------
// 5.8 MESSAGING PATTERNS (3)
// -----------------------------------------------------------------------------

// --- Pub/Sub ---
CREATE (:Pattern {
  name: 'Pub/Sub',
  category_name: 'Messaging',
  complexity: 'moderate',
  description: 'Publishers send messages to topics without knowledge of subscribers. Subscribers receive messages from topics they are interested in. Fully decouples producers from consumers.',
  when_to_use: 'When multiple consumers need to react to the same events, when producers should not know about consumers, in event-driven microservice architectures.',
  when_not_to_use: 'When point-to-point delivery with acknowledgment is required, or when message ordering is critical and hard to guarantee.',
  trade_offs: 'Full decoupling of publishers and subscribers and easy addition of new consumers vs. potential message loss, ordering challenges, and debugging difficulty.',
  implementation_notes: 'Use message brokers like Redis Pub/Sub, Kafka, or RabbitMQ. Topics partition messages by domain. Implement at-least-once delivery and idempotent consumers.'
});

// --- Dead Letter Queue ---
CREATE (:Pattern {
  name: 'Dead Letter Queue',
  category_name: 'Messaging',
  complexity: 'moderate',
  description: 'Stores messages that cannot be processed successfully after multiple attempts. Enables investigation, replay, and manual resolution of failed messages.',
  when_to_use: 'When message processing can fail and failed messages should not block the main queue, when you need to investigate and replay failed messages.',
  when_not_to_use: 'When all messages must be processed in order and failed messages should block subsequent processing until resolved.',
  trade_offs: 'Prevents queue blocking from poison messages and enables failure investigation vs. additional infrastructure and operational overhead for monitoring.',
  implementation_notes: 'Configure max retry count on main queue. Move messages to DLQ after exhausting retries. Store original message, error details, and retry count.'
});

// --- Saga ---
CREATE (:Pattern {
  name: 'Saga',
  category_name: 'Messaging',
  complexity: 'complex',
  description: 'Manages distributed transactions across multiple services using a sequence of local transactions with compensating actions for rollback on failure.',
  when_to_use: 'When business transactions span multiple microservices, when eventual consistency is acceptable, when two-phase commit is not feasible.',
  when_not_to_use: 'When strong consistency with ACID transactions is required, when the number of steps makes compensation overly complex.',
  trade_offs: 'Distributed transactions without two-phase commit and service autonomy vs. compensating transactions are complex and eventual consistency.',
  implementation_notes: 'Two approaches: orchestration (central coordinator) and choreography (event-driven). Each step has a compensating action for rollback.'
});

// -----------------------------------------------------------------------------
// 5.9 CACHING PATTERNS (3)
// -----------------------------------------------------------------------------

// --- Cache-Aside ---
CREATE (:Pattern {
  name: 'Cache-Aside',
  category_name: 'Caching',
  complexity: 'simple',
  description: 'Application code is responsible for loading data into the cache on cache misses. On read, check cache first; on miss, load from database and populate cache.',
  when_to_use: 'When read-heavy workloads benefit from caching, when the application can tolerate stale data for a TTL period.',
  when_not_to_use: 'When data changes frequently and staleness is unacceptable, or when write-heavy workloads make cache management overhead too high.',
  trade_offs: 'Simple to implement and only caches data that is actually read vs. potential cache stampede on expiration and stale data during TTL window.',
  implementation_notes: 'Check cache -> on miss, load from DB -> store in cache with TTL. Use cache stampede protection (locking or probabilistic early expiration).'
});

// --- Write-Through Cache ---
CREATE (:Pattern {
  name: 'Write-Through Cache',
  category_name: 'Caching',
  complexity: 'moderate',
  description: 'Writes data to both the cache and the underlying data store simultaneously. Ensures the cache always contains the latest data at the cost of write latency.',
  when_to_use: 'When read-after-write consistency is critical, when cache misses are expensive and should be minimized.',
  when_not_to_use: 'When write latency is critical and the double-write overhead is unacceptable, or when most written data is rarely read.',
  trade_offs: 'Always-consistent cache and no stale reads vs. increased write latency from dual writes and wasted cache space for rarely-read data.',
  implementation_notes: 'Write to cache and database in the same operation. Consider write-behind (async DB write) for lower latency at the cost of potential data loss.'
});

// --- Cache Invalidation ---
CREATE (:Pattern {
  name: 'Cache Invalidation',
  category_name: 'Caching',
  complexity: 'moderate',
  description: 'Strategies for removing or updating stale data from caches when the underlying data changes. One of the two hard problems in computer science.',
  when_to_use: 'Whenever caching is used and data correctness matters, when stale data causes business logic errors.',
  when_not_to_use: 'When data is immutable and never needs invalidation, or when TTL-based expiration provides sufficient freshness.',
  trade_offs: 'Data consistency between cache and source of truth vs. complexity of invalidation logic and potential for missed invalidations.',
  implementation_notes: 'Strategies: TTL-based expiration, event-driven invalidation, versioned keys, purge-on-write. Use pub/sub to broadcast invalidation events.'
});

// -----------------------------------------------------------------------------
// 5.10 SECURITY PATTERNS (3)
// -----------------------------------------------------------------------------

// --- Token-Based Auth ---
CREATE (:Pattern {
  name: 'Token-Based Auth',
  category_name: 'Security',
  complexity: 'moderate',
  description: 'Authenticates users by issuing tokens (JWT, OAuth2) after credential verification. Subsequent requests include the token for stateless authentication.',
  when_to_use: 'When building stateless APIs, when supporting multiple clients (web, mobile, third-party), when single sign-on is needed.',
  when_not_to_use: 'When session-based auth is simpler and sufficient, or when token storage on the client poses security risks.',
  trade_offs: 'Stateless authentication and cross-service compatibility vs. token revocation complexity and security risks if tokens are leaked.',
  implementation_notes: 'Use JWT with short expiration and refresh tokens. Store tokens securely (httpOnly cookies). Validate signature, expiration, and claims on every request.'
});

// --- RBAC ---
CREATE (:Pattern {
  name: 'RBAC',
  category_name: 'Security',
  complexity: 'moderate',
  description: 'Role-Based Access Control assigns permissions to roles rather than individual users. Users are assigned roles that determine what actions they can perform.',
  when_to_use: 'When access control needs to be managed at scale, when users fall into natural groupings with similar permission needs.',
  when_not_to_use: 'When access control requirements are attribute-based (ABAC) or when every user has unique permissions that do not fit role boundaries.',
  trade_offs: 'Simplified permission management and auditable access control vs. role explosion in complex systems and difficulty modeling fine-grained access.',
  implementation_notes: 'Define roles as collections of permissions. Assign users to roles. Check permissions via role lookup. Support role hierarchies for inheritance.'
});

// --- Input Validation ---
CREATE (:Pattern {
  name: 'Input Validation',
  category_name: 'Security',
  complexity: 'simple',
  description: 'Validates, sanitizes, and normalizes all user input before processing. Prevents injection attacks, data corruption, and unexpected behavior.',
  when_to_use: 'Always, on every input boundary: API endpoints, form submissions, file uploads, query parameters, headers, and any external data source.',
  when_not_to_use: 'There is no valid reason to skip input validation. It should always be applied at trust boundaries.',
  trade_offs: 'Protection against injection attacks and data integrity vs. development overhead for writing validation rules.',
  implementation_notes: 'Validate on the server side regardless of client-side validation. Use allowlists over denylists. Use Pydantic in Python, Zod in TypeScript.'
});

// =============================================================================
// 6. BELONGS_TO RELATIONSHIPS (Pattern -> Category)
// =============================================================================

// Creational
MATCH (p:Pattern {name: 'Singleton'}), (c:Category {name: 'Creational'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Factory Method'}), (c:Category {name: 'Creational'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Builder'}), (c:Category {name: 'Creational'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Abstract Factory'}), (c:Category {name: 'Creational'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Prototype'}), (c:Category {name: 'Creational'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Object Pool'}), (c:Category {name: 'Creational'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Dependency Injection'}), (c:Category {name: 'Creational'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Registry'}), (c:Category {name: 'Creational'}) CREATE (p)-[:BELONGS_TO]->(c);

// Structural
MATCH (p:Pattern {name: 'Adapter'}), (c:Category {name: 'Structural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Facade'}), (c:Category {name: 'Structural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Decorator'}), (c:Category {name: 'Structural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Proxy'}), (c:Category {name: 'Structural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Composite'}), (c:Category {name: 'Structural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Bridge'}), (c:Category {name: 'Structural'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Flyweight'}), (c:Category {name: 'Structural'}) CREATE (p)-[:BELONGS_TO]->(c);

// Behavioral
MATCH (p:Pattern {name: 'Observer'}), (c:Category {name: 'Behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Strategy'}), (c:Category {name: 'Behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Command'}), (c:Category {name: 'Behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Chain of Responsibility'}), (c:Category {name: 'Behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'State Machine'}), (c:Category {name: 'Behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Iterator'}), (c:Category {name: 'Behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Template Method'}), (c:Category {name: 'Behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Visitor'}), (c:Category {name: 'Behavioral'}) CREATE (p)-[:BELONGS_TO]->(c);

// Concurrency
MATCH (p:Pattern {name: 'Producer-Consumer'}), (c:Category {name: 'Concurrency'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Thread Pool'}), (c:Category {name: 'Concurrency'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Read-Write Lock'}), (c:Category {name: 'Concurrency'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Actor Model'}), (c:Category {name: 'Concurrency'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Semaphore'}), (c:Category {name: 'Concurrency'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Future/Promise'}), (c:Category {name: 'Concurrency'}) CREATE (p)-[:BELONGS_TO]->(c);

// Resilience
MATCH (p:Pattern {name: 'Circuit Breaker'}), (c:Category {name: 'Resilience'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Retry with Backoff'}), (c:Category {name: 'Resilience'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Bulkhead'}), (c:Category {name: 'Resilience'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Timeout'}), (c:Category {name: 'Resilience'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Fallback'}), (c:Category {name: 'Resilience'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Health Check'}), (c:Category {name: 'Resilience'}) CREATE (p)-[:BELONGS_TO]->(c);

// Data
MATCH (p:Pattern {name: 'Repository'}), (c:Category {name: 'Data'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Unit of Work'}), (c:Category {name: 'Data'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'CQRS'}), (c:Category {name: 'Data'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Event Sourcing'}), (c:Category {name: 'Data'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Data Transfer Object'}), (c:Category {name: 'Data'}) CREATE (p)-[:BELONGS_TO]->(c);

// API
MATCH (p:Pattern {name: 'API Gateway'}), (c:Category {name: 'API'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Backend for Frontend'}), (c:Category {name: 'API'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Pagination'}), (c:Category {name: 'API'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Idempotency'}), (c:Category {name: 'API'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Rate Limiting'}), (c:Category {name: 'API'}) CREATE (p)-[:BELONGS_TO]->(c);

// Messaging
MATCH (p:Pattern {name: 'Pub/Sub'}), (c:Category {name: 'Messaging'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Dead Letter Queue'}), (c:Category {name: 'Messaging'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Saga'}), (c:Category {name: 'Messaging'}) CREATE (p)-[:BELONGS_TO]->(c);

// Caching
MATCH (p:Pattern {name: 'Cache-Aside'}), (c:Category {name: 'Caching'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Write-Through Cache'}), (c:Category {name: 'Caching'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Cache Invalidation'}), (c:Category {name: 'Caching'}) CREATE (p)-[:BELONGS_TO]->(c);

// Security
MATCH (p:Pattern {name: 'Token-Based Auth'}), (c:Category {name: 'Security'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'RBAC'}), (c:Category {name: 'Security'}) CREATE (p)-[:BELONGS_TO]->(c);
MATCH (p:Pattern {name: 'Input Validation'}), (c:Category {name: 'Security'}) CREATE (p)-[:BELONGS_TO]->(c);

// =============================================================================
// 7. IMPLEMENTED_IN RELATIONSHIPS (Pattern -> Codebase)
// =============================================================================

MATCH (p:Pattern {name: 'Object Pool'}), (cb:Codebase {name: 'postgresql'})
CREATE (p)-[:IMPLEMENTED_IN {component: 'connection pooling', file_path: 'src/backend/utils/resowner.c'}]->(cb);

MATCH (p:Pattern {name: 'State Machine'}), (cb:Codebase {name: 'postgresql'})
CREATE (p)-[:IMPLEMENTED_IN {component: 'query executor', file_path: 'src/backend/executor/execMain.c'}]->(cb);

MATCH (p:Pattern {name: 'Observer'}), (cb:Codebase {name: 'redis'})
CREATE (p)-[:IMPLEMENTED_IN {component: 'pub/sub system', file_path: 'src/pubsub.c'}]->(cb);

MATCH (p:Pattern {name: 'Singleton'}), (cb:Codebase {name: 'redis'})
CREATE (p)-[:IMPLEMENTED_IN {component: 'server instance', file_path: 'src/server.c'}]->(cb);

MATCH (p:Pattern {name: 'Producer-Consumer'}), (cb:Codebase {name: 'linux-kernel'})
CREATE (p)-[:IMPLEMENTED_IN {component: 'work queues', file_path: 'kernel/workqueue.c'}]->(cb);

MATCH (p:Pattern {name: 'Read-Write Lock'}), (cb:Codebase {name: 'linux-kernel'})
CREATE (p)-[:IMPLEMENTED_IN {component: 'rwlock', file_path: 'kernel/locking/rwsem.c'}]->(cb);

MATCH (p:Pattern {name: 'Circuit Breaker'}), (cb:Codebase {name: 'kubernetes'})
CREATE (p)-[:IMPLEMENTED_IN {component: 'API server', file_path: 'staging/src/k8s.io/apiserver/pkg/server/filters/maxinflight.go'}]->(cb);

MATCH (p:Pattern {name: 'Repository'}), (cb:Codebase {name: 'sentry'})
CREATE (p)-[:IMPLEMENTED_IN {component: 'data access layer', file_path: 'src/sentry/models/'}]->(cb);

MATCH (p:Pattern {name: 'Future/Promise'}), (cb:Codebase {name: 'tokio'})
CREATE (p)-[:IMPLEMENTED_IN {component: 'async runtime core', file_path: 'tokio/src/runtime/'}]->(cb);

MATCH (p:Pattern {name: 'Dependency Injection'}), (cb:Codebase {name: 'fastapi'})
CREATE (p)-[:IMPLEMENTED_IN {component: 'Depends() system', file_path: 'fastapi/dependencies/'}]->(cb);

// =============================================================================
// 8. OFTEN_COMBINED_WITH RELATIONSHIPS (bidirectional)
// =============================================================================

// Repository <-> Unit of Work
MATCH (a:Pattern {name: 'Repository'}), (b:Pattern {name: 'Unit of Work'})
CREATE (a)-[:OFTEN_COMBINED_WITH {reason: 'CRUD + transaction coordination'}]->(b);
MATCH (a:Pattern {name: 'Repository'}), (b:Pattern {name: 'Unit of Work'})
CREATE (b)-[:OFTEN_COMBINED_WITH {reason: 'CRUD + transaction coordination'}]->(a);

// Circuit Breaker <-> Retry with Backoff
MATCH (a:Pattern {name: 'Circuit Breaker'}), (b:Pattern {name: 'Retry with Backoff'})
CREATE (a)-[:OFTEN_COMBINED_WITH {reason: 'Retry within breaker bounds prevents cascade'}]->(b);
MATCH (a:Pattern {name: 'Circuit Breaker'}), (b:Pattern {name: 'Retry with Backoff'})
CREATE (b)-[:OFTEN_COMBINED_WITH {reason: 'Retry within breaker bounds prevents cascade'}]->(a);

// Circuit Breaker <-> Fallback
MATCH (a:Pattern {name: 'Circuit Breaker'}), (b:Pattern {name: 'Fallback'})
CREATE (a)-[:OFTEN_COMBINED_WITH {reason: 'Degraded service when circuit open'}]->(b);
MATCH (a:Pattern {name: 'Circuit Breaker'}), (b:Pattern {name: 'Fallback'})
CREATE (b)-[:OFTEN_COMBINED_WITH {reason: 'Degraded service when circuit open'}]->(a);

// CQRS <-> Event Sourcing
MATCH (a:Pattern {name: 'CQRS'}), (b:Pattern {name: 'Event Sourcing'})
CREATE (a)-[:OFTEN_COMBINED_WITH {reason: 'Events naturally support separate read/write'}]->(b);
MATCH (a:Pattern {name: 'CQRS'}), (b:Pattern {name: 'Event Sourcing'})
CREATE (b)-[:OFTEN_COMBINED_WITH {reason: 'Events naturally support separate read/write'}]->(a);

// Factory Method <-> Strategy
MATCH (a:Pattern {name: 'Factory Method'}), (b:Pattern {name: 'Strategy'})
CREATE (a)-[:OFTEN_COMBINED_WITH {reason: 'Factory creates appropriate strategy'}]->(b);
MATCH (a:Pattern {name: 'Factory Method'}), (b:Pattern {name: 'Strategy'})
CREATE (b)-[:OFTEN_COMBINED_WITH {reason: 'Factory creates appropriate strategy'}]->(a);

// API Gateway <-> Rate Limiting
MATCH (a:Pattern {name: 'API Gateway'}), (b:Pattern {name: 'Rate Limiting'})
CREATE (a)-[:OFTEN_COMBINED_WITH {reason: 'Gateway enforces rate limits'}]->(b);
MATCH (a:Pattern {name: 'API Gateway'}), (b:Pattern {name: 'Rate Limiting'})
CREATE (b)-[:OFTEN_COMBINED_WITH {reason: 'Gateway enforces rate limits'}]->(a);

// API Gateway <-> Token-Based Auth
MATCH (a:Pattern {name: 'API Gateway'}), (b:Pattern {name: 'Token-Based Auth'})
CREATE (a)-[:OFTEN_COMBINED_WITH {reason: 'Gateway validates tokens before routing'}]->(b);
MATCH (a:Pattern {name: 'API Gateway'}), (b:Pattern {name: 'Token-Based Auth'})
CREATE (b)-[:OFTEN_COMBINED_WITH {reason: 'Gateway validates tokens before routing'}]->(a);

// Cache-Aside <-> Cache Invalidation
MATCH (a:Pattern {name: 'Cache-Aside'}), (b:Pattern {name: 'Cache Invalidation'})
CREATE (a)-[:OFTEN_COMBINED_WITH {reason: 'Every cache needs invalidation strategy'}]->(b);
MATCH (a:Pattern {name: 'Cache-Aside'}), (b:Pattern {name: 'Cache Invalidation'})
CREATE (b)-[:OFTEN_COMBINED_WITH {reason: 'Every cache needs invalidation strategy'}]->(a);

// Pub/Sub <-> Dead Letter Queue
MATCH (a:Pattern {name: 'Pub/Sub'}), (b:Pattern {name: 'Dead Letter Queue'})
CREATE (a)-[:OFTEN_COMBINED_WITH {reason: 'Failed messages need somewhere to go'}]->(b);
MATCH (a:Pattern {name: 'Pub/Sub'}), (b:Pattern {name: 'Dead Letter Queue'})
CREATE (b)-[:OFTEN_COMBINED_WITH {reason: 'Failed messages need somewhere to go'}]->(a);

// Observer <-> Pub/Sub
MATCH (a:Pattern {name: 'Observer'}), (b:Pattern {name: 'Pub/Sub'})
CREATE (a)-[:OFTEN_COMBINED_WITH {reason: 'Pub/Sub is distributed Observer'}]->(b);
MATCH (a:Pattern {name: 'Observer'}), (b:Pattern {name: 'Pub/Sub'})
CREATE (b)-[:OFTEN_COMBINED_WITH {reason: 'Pub/Sub is distributed Observer'}]->(a);

// Dependency Injection <-> Factory Method
MATCH (a:Pattern {name: 'Dependency Injection'}), (b:Pattern {name: 'Factory Method'})
CREATE (a)-[:OFTEN_COMBINED_WITH {reason: 'Factory creates injected dependencies'}]->(b);
MATCH (a:Pattern {name: 'Dependency Injection'}), (b:Pattern {name: 'Factory Method'})
CREATE (b)-[:OFTEN_COMBINED_WITH {reason: 'Factory creates injected dependencies'}]->(a);

// Producer-Consumer <-> Thread Pool
MATCH (a:Pattern {name: 'Producer-Consumer'}), (b:Pattern {name: 'Thread Pool'})
CREATE (a)-[:OFTEN_COMBINED_WITH {reason: 'Workers consume from queue'}]->(b);
MATCH (a:Pattern {name: 'Producer-Consumer'}), (b:Pattern {name: 'Thread Pool'})
CREATE (b)-[:OFTEN_COMBINED_WITH {reason: 'Workers consume from queue'}]->(a);

// =============================================================================
// 9. CONFLICTS_WITH RELATIONSHIPS (bidirectional)
// =============================================================================

// Singleton <-> Dependency Injection
MATCH (a:Pattern {name: 'Singleton'}), (b:Pattern {name: 'Dependency Injection'})
CREATE (a)-[:CONFLICTS_WITH {reason: 'Singleton hides dependencies, DI makes them explicit. Prefer DI.'}]->(b);
MATCH (a:Pattern {name: 'Singleton'}), (b:Pattern {name: 'Dependency Injection'})
CREATE (b)-[:CONFLICTS_WITH {reason: 'Singleton hides dependencies, DI makes them explicit. Prefer DI.'}]->(a);

// Event Sourcing <-> Cache-Aside
MATCH (a:Pattern {name: 'Event Sourcing'}), (b:Pattern {name: 'Cache-Aside'})
CREATE (a)-[:CONFLICTS_WITH {reason: 'Event sourcing rebuilds from events, making traditional caching complex. Use projections.'}]->(b);
MATCH (a:Pattern {name: 'Event Sourcing'}), (b:Pattern {name: 'Cache-Aside'})
CREATE (b)-[:CONFLICTS_WITH {reason: 'Event sourcing rebuilds from events, making traditional caching complex. Use projections.'}]->(a);

// =============================================================================
// 10. HAS_TEMPLATE_FOR RELATIONSHIPS (Pattern -> Language)
// =============================================================================

MATCH (p:Pattern {name: 'Singleton'}), (l:Language {name: 'Python'})
CREATE (p)-[:HAS_TEMPLATE_FOR]->(l);
MATCH (p:Pattern {name: 'Singleton'}), (l:Language {name: 'Go'})
CREATE (p)-[:HAS_TEMPLATE_FOR]->(l);
MATCH (p:Pattern {name: 'Singleton'}), (l:Language {name: 'Rust'})
CREATE (p)-[:HAS_TEMPLATE_FOR]->(l);

MATCH (p:Pattern {name: 'Factory Method'}), (l:Language {name: 'Python'})
CREATE (p)-[:HAS_TEMPLATE_FOR]->(l);
MATCH (p:Pattern {name: 'Factory Method'}), (l:Language {name: 'Go'})
CREATE (p)-[:HAS_TEMPLATE_FOR]->(l);

// =============================================================================
// 11. ANTI-PATTERNS (8)
// =============================================================================

CREATE (:AntiPattern {name: 'God Class', severity: 'high', description: 'Single class does too much — split into focused classes behind well-defined interfaces.'});
CREATE (:AntiPattern {name: 'Hardcoded Secrets', severity: 'critical', description: 'Credentials embedded in source code — use Vault, environment variables, or secret managers.'});
CREATE (:AntiPattern {name: 'N+1 Query', severity: 'high', description: 'Fetching related data in a loop instead of batching — use JOINs, eager loading, or batch APIs.'});
CREATE (:AntiPattern {name: 'No Error Handling', severity: 'high', description: 'Bare except clauses or swallowing errors — catch specific exceptions, log context, handle gracefully.'});
CREATE (:AntiPattern {name: 'Unbounded Queries', severity: 'medium', description: 'SELECT * without LIMIT or pagination — always set bounds on result sets.'});
CREATE (:AntiPattern {name: 'Synchronous External Calls', severity: 'medium', description: 'Blocking on external services in the request path — use async processing or message queues.'});
CREATE (:AntiPattern {name: 'Missing Input Validation', severity: 'critical', description: 'Trusting user input without validation — validate type, length, range, and format at every boundary.'});
CREATE (:AntiPattern {name: 'Circular Dependencies', severity: 'high', description: 'Module A depends on B which depends on A — break cycles with event bus, mediator, or dependency inversion.'});

// =============================================================================
// 12. FIXED_BY RELATIONSHIPS (AntiPattern -> Pattern)
// =============================================================================

MATCH (a:AntiPattern {name: 'God Class'}), (p:Pattern {name: 'Facade'})
CREATE (a)-[:FIXED_BY]->(p);

MATCH (a:AntiPattern {name: 'Hardcoded Secrets'}), (p:Pattern {name: 'Dependency Injection'})
CREATE (a)-[:FIXED_BY]->(p);

MATCH (a:AntiPattern {name: 'N+1 Query'}), (p:Pattern {name: 'Repository'})
CREATE (a)-[:FIXED_BY]->(p);

MATCH (a:AntiPattern {name: 'No Error Handling'}), (p:Pattern {name: 'Circuit Breaker'})
CREATE (a)-[:FIXED_BY]->(p);

MATCH (a:AntiPattern {name: 'Unbounded Queries'}), (p:Pattern {name: 'Pagination'})
CREATE (a)-[:FIXED_BY]->(p);

MATCH (a:AntiPattern {name: 'Synchronous External Calls'}), (p:Pattern {name: 'Producer-Consumer'})
CREATE (a)-[:FIXED_BY]->(p);

MATCH (a:AntiPattern {name: 'Missing Input Validation'}), (p:Pattern {name: 'Input Validation'})
CREATE (a)-[:FIXED_BY]->(p);

MATCH (a:AntiPattern {name: 'Circular Dependencies'}), (p:Pattern {name: 'Pub/Sub'})
CREATE (a)-[:FIXED_BY]->(p);

// =============================================================================
// SEED COMPLETE — 54 patterns, 10 categories, 6 languages, 8 codebases,
//                 8 anti-patterns, all relationships established
// =============================================================================
