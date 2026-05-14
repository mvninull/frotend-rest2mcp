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
];

let tarefas_db = [
  { id: 1, titulo: 'Comprar leite', concluida: false, criada_em: '2024-01-15T10:30:00Z' },
  { id: 2, titulo: 'Estudar Python', concluida: true, criada_em: '2024-01-15T10:31:00Z' },
  { id: 3, titulo: 'Fazer exercícios', concluida: false, criada_em: '2024-01-15T10:32:00Z' },
];

async function bootstrap() {
  const app = Fastify({ logger: true });

  await app.register(fastifySwagger, {
    openapi: {
      info: {
        title: 'Tarefas API',
        description: 'API simples de tarefas (todo list)',
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

  const TarefaJsonSchema = {
    type: 'object',
    properties: {
      id: { type: 'integer', description: 'ID da tarefa' },
      titulo: { type: 'string', description: 'Título da tarefa' },
      concluida: { type: 'boolean', description: 'Tarefa concluída' },
      criada_em: { type: 'string', format: 'date-time', description: 'Data de criação' },
    },
    example: { id: 1, titulo: 'Comprar leite', concluida: false, criada_em: '2024-01-15T10:30:00Z' },
  };

  const ErrorJsonSchema = {
    type: 'object',
    properties: { detail: { type: 'string', description: 'Mensagem de erro' } },
  };

  // === HOME ===
  app.get('/api/v1/', {
    schema: {
      tags: ['Root'],
      summary: 'Home',
      response: { 200: { type: 'object', properties: { message: { type: 'string' }, docs: { type: 'string' } } } },
    },
  }, async () => ({ message: 'Bem-vindo à Tarefas API', docs: '/docs' }));

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

  // === TAREFAS ===
  app.get('/api/v1/tarefas', {
    schema: {
      tags: ['Tarefas'],
      summary: 'Listar tarefas',
      security: [bearerAuth],
      querystring: {
        type: 'object',
        properties: {
          concluida: { type: 'boolean', description: 'Filtrar por status' },
        },
      },
      response: { 200: { type: 'array', items: TarefaJsonSchema } },
    },
    onRequest: authHook,
  }, async (request) => {
    if (request.query.concluida === undefined) return tarefas_db;
    return tarefas_db.filter(t => t.concluida === request.query.concluida);
  });

  app.post('/api/v1/tarefas', {
    schema: {
      tags: ['Tarefas'],
      summary: 'Adicionar tarefa',
      security: [bearerAuth],
      body: {
        type: 'object',
        required: ['titulo'],
        properties: {
          titulo: { type: 'string', minLength: 1, maxLength: 200, description: 'Título da tarefa' },
        },
      },
      response: { 201: TarefaJsonSchema },
    },
    onRequest: authHook,
  }, async (request, reply) => {
    const novo_id = tarefas_db.length > 0 ? Math.max(...tarefas_db.map(t => t.id)) + 1 : 1;
    const tarefa = {
      id: novo_id,
      titulo: request.body.titulo,
      concluida: false,
      criada_em: new Date().toISOString(),
    };
    tarefas_db.push(tarefa);
    reply.status(201);
    return tarefa;
  });

  app.delete('/api/v1/tarefas/:tarefa_id', {
    schema: {
      tags: ['Tarefas'],
      summary: 'Remover tarefa',
      security: [bearerAuth],
      params: {
        type: 'object',
        required: ['tarefa_id'],
        properties: { tarefa_id: { type: 'integer', description: 'ID da tarefa' } },
      },
      response: {
        204: { type: 'null', description: 'Tarefa deletada com sucesso' },
        404: { description: 'Tarefa não encontrada', ...ErrorJsonSchema },
      },
    },
    onRequest: authHook,
  }, async (request, reply) => {
    const idx = tarefas_db.findIndex(t => t.id === Number(request.params.tarefa_id));
    if (idx === -1) return reply.status(404).send({ detail: 'Tarefa não encontrada' });
    tarefas_db.splice(idx, 1);
    reply.status(204);
  });

  await app.ready();
  console.log('Iniciando Tarefas API...');
  console.log('Swagger UI: http://localhost:8001/docs');
  console.log('API Base: http://localhost:8001/api/v1/');
  await app.listen({ port: 8001, host: '0.0.0.0' });
}

bootstrap();
