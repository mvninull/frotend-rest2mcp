const Fastify = require('fastify');
const fastifySwagger = require('@fastify/swagger');
const fastifySwaggerUi = require('@fastify/swagger-ui');
const crypto = require('crypto');

const SECRET = 'super-secret-key-mude-em-producao';

function base64url(buf) {
  return buf.toString('base64url');
}

function signJWT(payload) {
  const header = base64url(Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })));
  const body = base64url(Buffer.from(JSON.stringify({ ...payload, exp: Math.floor(Date.now() / 1000) + 3600 })));
  const signature = base64url(crypto.createHmac('sha256', SECRET).update(`${header}.${body}`).digest());
  return `${header}.${body}.${signature}`;
}

function verifyJWT(token) {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const signature = base64url(crypto.createHmac('sha256', SECRET).update(`${parts[0]}.${parts[1]}`).digest());
    if (signature !== parts[2]) return null;
    const payload = JSON.parse(Buffer.from(parts[1], 'base64url').toString());
    if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) return null;
    return payload;
  } catch {
    return null;
  }
}

function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.pbkdf2Sync(password, salt, 10000, 64, 'sha512').toString('hex');
  return `${salt}:${hash}`;
}

function verifyPassword(password, stored) {
  const [salt, hash] = stored.split(':');
  const computed = crypto.pbkdf2Sync(password, salt, 10000, 64, 'sha512').toString('hex');
  return hash === computed;
}

const fake_users_db = [
  { username: 'admin', hashed_password: hashPassword('123456'), nome: 'Administrador' },
  { username: 'user', hashed_password: hashPassword('senha123'), nome: 'Usuário Teste' },
];

let produtos_db = [
  { id: 1, nome: 'Notebook Dell', preco: 4500.00, categoria: 'Eletrônicos', em_estoque: true, criado_em: '2024-01-15T10:30:00Z' },
  { id: 2, nome: 'Mouse Logitech', preco: 150.00, categoria: 'Periféricos', em_estoque: true, criado_em: '2024-01-15T10:31:00Z' },
  { id: 3, nome: 'Teclado Mecânico', preco: 350.00, categoria: 'Periféricos', em_estoque: false, criado_em: '2024-01-15T10:32:00Z' },
  { id: 4, nome: 'Monitor 27', preco: 1200.00, categoria: 'Eletrônicos', em_estoque: true, criado_em: '2024-01-15T10:33:00Z' },
];

async function bootstrap() {
  const app = Fastify({ logger: true });

  await app.register(fastifySwagger, {
    openapi: {
      info: {
        title: 'Loja API',
        description: 'API simples de demonstração para teste de auto-discovery',
        version: '1.0.0',
      },
      components: {
        securitySchemes: {
          BearerAuth: {
            type: 'http',
            scheme: 'bearer',
            bearerFormat: 'JWT',
          },
        },
      },
    },
  });

  await app.register(fastifySwaggerUi, {
    routePrefix: '/docs',
    uiConfig: { persistAuthorization: true },
  });

  const bearerAuth = { BearerAuth: [] };

  async function authHook(request, reply) {
    const auth = request.headers.authorization;
    if (!auth || !auth.startsWith('Bearer ')) {
      return reply.status(401).send({ detail: 'Token inválido ou expirado' });
    }
    const payload = verifyJWT(auth.slice(7));
    if (!payload) {
      return reply.status(401).send({ detail: 'Token inválido ou expirado' });
    }
    request.user = fake_users_db.find(u => u.username === payload.sub);
    if (!request.user) {
      return reply.status(401).send({ detail: 'Usuário não encontrado' });
    }
  }

  const ProdutoJsonSchema = {
    type: 'object',
    properties: {
      id: { type: 'integer', description: 'ID único do produto' },
      nome: { type: 'string', description: 'Nome do produto' },
      preco: { type: 'number', description: 'Preço em reais' },
      categoria: { type: 'string', description: 'Categoria do produto' },
      em_estoque: { type: 'boolean', description: 'Disponível em estoque' },
      criado_em: { type: 'string', format: 'date-time', description: 'Data de criação' },
    },
    example: {
      id: 1, nome: 'Notebook Dell', preco: 4500.00, categoria: 'Eletrônicos',
      em_estoque: true, criado_em: '2024-01-15T10:30:00Z',
    },
  };

  const ErrorJsonSchema = {
    type: 'object',
    properties: { detail: { type: 'string', description: 'Mensagem de erro' } },
  };

  // === HOME ===
  app.get('/', {
    schema: {
      tags: ['Root'],
      summary: 'Home',
      response: { 200: { type: 'object', properties: { message: { type: 'string' }, docs: { type: 'string' } } } },
    },
  }, async () => ({ message: 'Bem-vindo à Loja API', docs: '/docs' }));

  // === AUTH ===
  app.post('/api/v1/auth/login', {
    schema: {
      tags: ['Autenticação'],
      summary: 'Login',
      body: {
        type: 'object',
        required: ['username', 'password'],
        properties: {
          username: { type: 'string', description: 'Nome de usuário' },
          password: { type: 'string', description: 'Senha do usuário' },
        },
      },
      response: {
        200: {
          type: 'object',
          properties: { access_token: { type: 'string' }, token_type: { type: 'string' } },
        },
        401: { description: 'Usuário ou senha inválidos', ...ErrorJsonSchema },
      },
    },
  }, async (request, reply) => {
    const { username, password } = request.body;
    const user = fake_users_db.find(u => u.username === username);
    if (!user || !verifyPassword(password, user.hashed_password)) {
      return reply.status(401).send({ detail: 'Usuário ou senha inválidos' });
    }
    return { access_token: signJWT({ sub: user.username }), token_type: 'bearer' };
  });

  app.get('/api/v1/auth/me', {
    schema: {
      tags: ['Autenticação'],
      summary: 'Dados do usuário atual',
      security: [bearerAuth],
      response: {
        200: { type: 'object', properties: { username: { type: 'string' }, nome: { type: 'string' } } },
      },
    },
    onRequest: authHook,
  }, async (request) => ({
    username: request.user.username,
    nome: request.user.nome,
  }));

  // === PRODUTOS ===
  app.get('/api/v1/produtos', {
    schema: {
      tags: ['Produtos'],
      summary: 'Listar todos os produtos',
      security: [bearerAuth],
      querystring: {
        type: 'object',
        properties: {
          categoria: { type: 'string', description: 'Filtrar por categoria' },
          em_estoque: { type: 'boolean', description: 'Filtrar por disponibilidade' },
        },
      },
      response: { 200: { type: 'array', items: ProdutoJsonSchema } },
    },
    onRequest: authHook,
  }, async (request) => {
    let result = produtos_db;
    if (request.query.categoria) {
      result = result.filter(p => p.categoria.toLowerCase() === request.query.categoria.toLowerCase());
    }
    if (request.query.em_estoque !== undefined) {
      result = result.filter(p => p.em_estoque === request.query.em_estoque);
    }
    return result;
  });

  app.get('/api/v1/produtos/:produto_id', {
    schema: {
      tags: ['Produtos'],
      summary: 'Buscar produto por ID',
      security: [bearerAuth],
      params: {
        type: 'object',
        required: ['produto_id'],
        properties: { produto_id: { type: 'integer', description: 'ID do produto' } },
      },
      response: { 200: ProdutoJsonSchema, 404: { description: 'Produto não encontrado', ...ErrorJsonSchema } },
    },
    onRequest: authHook,
  }, async (request, reply) => {
    const produto = produtos_db.find(p => p.id === Number(request.params.produto_id));
    if (!produto) return reply.status(404).send({ detail: `Produto ${request.params.produto_id} não encontrado` });
    return produto;
  });

  app.post('/api/v1/produtos', {
    schema: {
      tags: ['Produtos'],
      summary: 'Criar novo produto',
      security: [bearerAuth],
      body: {
        type: 'object',
        required: ['nome', 'preco', 'categoria'],
        properties: {
          nome: { type: 'string', minLength: 2, maxLength: 100, description: 'Nome do produto' },
          preco: { type: 'number', exclusiveMinimum: 0, description: 'Preço em reais' },
          categoria: { type: 'string', description: 'Categoria do produto' },
          em_estoque: { type: 'boolean', description: 'Disponível em estoque', default: true },
        },
      },
      response: { 201: ProdutoJsonSchema },
    },
    onRequest: authHook,
  }, async (request, reply) => {
    const novo_id = Math.max(...produtos_db.map(p => p.id)) + 1;
    const produto = {
      id: novo_id,
      nome: request.body.nome,
      preco: request.body.preco,
      categoria: request.body.categoria,
      em_estoque: request.body.em_estoque !== undefined ? request.body.em_estoque : true,
      criado_em: new Date().toISOString(),
    };
    produtos_db.push(produto);
    reply.status(201);
    return produto;
  });

  app.put('/api/v1/produtos/:produto_id', {
    schema: {
      tags: ['Produtos'],
      summary: 'Atualizar produto',
      security: [bearerAuth],
      params: {
        type: 'object',
        required: ['produto_id'],
        properties: { produto_id: { type: 'integer', description: 'ID do produto' } },
      },
      body: {
        type: 'object',
        properties: {
          nome: { type: 'string', minLength: 2, maxLength: 100 },
          preco: { type: 'number', exclusiveMinimum: 0 },
          categoria: { type: 'string' },
          em_estoque: { type: 'boolean' },
        },
      },
      response: { 200: ProdutoJsonSchema, 404: { description: 'Produto não encontrado', ...ErrorJsonSchema } },
    },
    onRequest: authHook,
  }, async (request, reply) => {
    const idx = produtos_db.findIndex(p => p.id === Number(request.params.produto_id));
    if (idx === -1) return reply.status(404).send({ detail: `Produto ${request.params.produto_id} não encontrado` });
    const dados = request.body;
    if (dados.nome !== undefined) produtos_db[idx].nome = dados.nome;
    if (dados.preco !== undefined) produtos_db[idx].preco = dados.preco;
    if (dados.categoria !== undefined) produtos_db[idx].categoria = dados.categoria;
    if (dados.em_estoque !== undefined) produtos_db[idx].em_estoque = dados.em_estoque;
    return produtos_db[idx];
  });

  app.delete('/api/v1/produtos/:produto_id', {
    schema: {
      tags: ['Produtos'],
      summary: 'Deletar produto',
      security: [bearerAuth],
      params: {
        type: 'object',
        required: ['produto_id'],
        properties: { produto_id: { type: 'integer', description: 'ID do produto' } },
      },
      response: { 204: { type: 'null', description: 'Produto deletado com sucesso' }, 404: { description: 'Produto não encontrado', ...ErrorJsonSchema } },
    },
    onRequest: authHook,
  }, async (request, reply) => {
    const idx = produtos_db.findIndex(p => p.id === Number(request.params.produto_id));
    if (idx === -1) return reply.status(404).send({ detail: `Produto ${request.params.produto_id} não encontrado` });
    produtos_db.splice(idx, 1);
    reply.status(204);
  });

  // === CATEGORIAS ===
  app.get('/api/v1/categorias', {
    schema: {
      tags: ['Categorias'],
      summary: 'Listar categorias',
      security: [bearerAuth],
      response: {
        200: {
          type: 'object',
          properties: {
            categorias: { type: 'array', items: { type: 'string' } },
            total: { type: 'integer' },
          },
        },
      },
    },
    onRequest: authHook,
  }, async () => {
    const categorias = [...new Set(produtos_db.map(p => p.categoria))];
    return { categorias, total: categorias.length };
  });

  await app.ready();
  console.log('Iniciando Loja API...');
  console.log('Swagger UI: http://localhost:8089/docs');
  await app.listen({ port: 8089, host: '0.0.0.0' });
}

bootstrap();
