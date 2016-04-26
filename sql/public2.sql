/*
 Navicat Premium Data Transfer

 Source Server         : Crane ojo-streamer db
 Source Server Type    : PostgreSQL
 Source Server Version : 90213
 Source Host           : ec2-54-83-32-64.compute-1.amazonaws.com
 Source Database       : d6or7541hmg7qi
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 90213
 File Encoding         : utf-8

 Date: 04/13/2016 08:38:25 AM
*/

-- ----------------------------
--  Sequence structure for app_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."app_seq";
CREATE SEQUENCE "public"."app_seq" INCREMENT 1 START 2 MAXVALUE 9223372036854775807 MINVALUE 1 CACHE 1;
ALTER TABLE "public"."app_seq" OWNER TO "rccp";

-- ----------------------------
--  Sequence structure for download_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."download_seq";
CREATE SEQUENCE "public"."download_seq" INCREMENT 1 START 469 MAXVALUE 9223372036854775807 MINVALUE 1 CACHE 1;
ALTER TABLE "public"."download_seq" OWNER TO "rccp";

-- ----------------------------
--  Sequence structure for id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."id_seq";
CREATE SEQUENCE "public"."id_seq" INCREMENT 1 START 14 MAXVALUE 9223372036854775807 MINVALUE 1 CACHE 1;
ALTER TABLE "public"."id_seq" OWNER TO "rccp";

-- ----------------------------
--  Sequence structure for landslide_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."landslide_seq";
CREATE SEQUENCE "public"."landslide_seq" INCREMENT 1 START 7628 MAXVALUE 9223372036854775807 MINVALUE 1 CACHE 1;
ALTER TABLE "public"."landslide_seq" OWNER TO "rccp";

-- ----------------------------
--  Sequence structure for user_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."user_seq";
CREATE SEQUENCE "public"."user_seq" INCREMENT 1 START 231 MAXVALUE 9223372036854775807 MINVALUE 1 CACHE 1;
ALTER TABLE "public"."user_seq" OWNER TO "rccp";


-- ----------------------------
--  Table structure for actions
-- ----------------------------
DROP TABLE IF EXISTS "public"."actions";
CREATE TABLE "public"."actions" (
	"data_type" char(1) NOT NULL COLLATE "default",
	"action" char(1) NOT NULL COLLATE "default",
	"id" int8 NOT NULL
)
WITH (OIDS=FALSE);
ALTER TABLE "public"."actions" OWNER TO "rccp";

-- ----------------------------
--  Table structure for schema_info
-- ----------------------------
DROP TABLE IF EXISTS "public"."schema_info";
CREATE TABLE "public"."schema_info" (
	"version" int4 NOT NULL
)
WITH (OIDS=FALSE);
ALTER TABLE "public"."schema_info" OWNER TO "rccp";

-- ----------------------------
--  Table structure for applications
-- ----------------------------
DROP TABLE IF EXISTS "public"."applications";
CREATE TABLE "public"."applications" (
	"id" int4 NOT NULL DEFAULT nextval('app_seq'::regclass),
	"name" text COLLATE "default",
	"description" text COLLATE "default",
	"link" text COLLATE "default",
	"icon_url" text COLLATE "default",
	"logo_url" text COLLATE "default",
	"company" text COLLATE "default",
	"secret" text COLLATE "default",
	"created_at" timestamp(6) NULL,
	"updated_at" timestamp(6) NULL,
	"status" text COLLATE "default",
	"fbappid" text COLLATE "default"
)
WITH (OIDS=FALSE);
ALTER TABLE "public"."applications" OWNER TO "rccp";

-- ----------------------------
--  Table structure for useage
-- ----------------------------
DROP TABLE IF EXISTS "public"."useage";
CREATE TABLE "public"."useage" (
	"user_id" int4 NOT NULL,
	"date" timestamp(6) NOT NULL,
	"location" varchar NOT NULL COLLATE "default",
	"what" varchar NOT NULL COLLATE "default",
	"contents" varchar NOT NULL COLLATE "default"
)
WITH (OIDS=FALSE);
ALTER TABLE "public"."useage" OWNER TO "rccp";

-- ----------------------------
--  Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS "public"."users";
CREATE TABLE "public"."users" (
	"id" int4 NOT NULL DEFAULT nextval('user_seq'::regclass),
	"name" varchar NOT NULL COLLATE "default",
	"email" varchar COLLATE "default",
	"organization" varchar COLLATE "default",
	"created_at" timestamp(6) NULL,
	"updated_at" timestamp(6) NULL,
	"is_admin" bool,
	"is_banned" bool,
	"gravatar" varchar COLLATE "default",
	"cat_src" varchar COLLATE "default",
	"latitude" float4,
	"longitude" float4,
	"lang" varchar COLLATE "default",
	"region" varchar COLLATE "default",
	"license_accepted" bool
)
WITH (OIDS=FALSE);
ALTER TABLE "public"."users" OWNER TO "rccp";

-- ----------------------------
--  Table structure for downloads
-- ----------------------------
DROP TABLE IF EXISTS "public"."downloads";
CREATE TABLE "public"."downloads" (
	"id" int4 NOT NULL DEFAULT nextval('download_seq'::regclass),
	"ip" varchar NOT NULL COLLATE "default",
	"date" date NOT NULL,
	"fmt" varchar NOT NULL COLLATE "default",
	"count" int4 NOT NULL,
	"elts" varchar NOT NULL COLLATE "default",
	"user_id" int4
)
WITH (OIDS=FALSE);
ALTER TABLE "public"."downloads" OWNER TO "rccp";

-- ----------------------------
--  Table structure for session
-- ----------------------------
DROP TABLE IF EXISTS "public"."session";
CREATE TABLE "public"."session" (
	"sid" varchar NOT NULL COLLATE "default",
	"sess" json NOT NULL,
	"expire" timestamp(6) NOT NULL
)
WITH (OIDS=FALSE);
ALTER TABLE "public"."session" OWNER TO "rccp";


-- ----------------------------
--  Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."app_seq" RESTART 3;
ALTER SEQUENCE "public"."download_seq" RESTART 470;
ALTER SEQUENCE "public"."id_seq" RESTART 15;
ALTER SEQUENCE "public"."landslide_seq" RESTART 7629;
ALTER SEQUENCE "public"."user_seq" RESTART 232;

-- ----------------------------
--  Primary key structure for table actions
-- ----------------------------
ALTER TABLE "public"."actions" ADD PRIMARY KEY ("data_type", "id") NOT DEFERRABLE INITIALLY IMMEDIATE;

-- ----------------------------
--  Primary key structure for table schema_info
-- ----------------------------
ALTER TABLE "public"."schema_info" ADD PRIMARY KEY ("version") NOT DEFERRABLE INITIALLY IMMEDIATE;

-- ----------------------------
--  Primary key structure for table applications
-- ----------------------------
ALTER TABLE "public"."applications" ADD PRIMARY KEY ("id") NOT DEFERRABLE INITIALLY IMMEDIATE;

-- ----------------------------
--  Primary key structure for table users
-- ----------------------------
ALTER TABLE "public"."users" ADD PRIMARY KEY ("id") NOT DEFERRABLE INITIALLY IMMEDIATE;

-- ----------------------------
--  Primary key structure for table downloads
-- ----------------------------
ALTER TABLE "public"."downloads" ADD PRIMARY KEY ("id") NOT DEFERRABLE INITIALLY IMMEDIATE;

-- ----------------------------
--  Primary key structure for table session
-- ----------------------------
ALTER TABLE "public"."session" ADD PRIMARY KEY ("sid") NOT DEFERRABLE INITIALLY IMMEDIATE;

