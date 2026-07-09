-- 为已存在的 rating 表补加 (user_id, media_id) 唯一约束，防止并发重复行。
-- 执行前请先确认没有重复数据；如有重复，先去重再执行。

-- 1) 查看重复行（若有结果需先处理）
-- SELECT user_id, media_id, COUNT(*) c FROM rating GROUP BY user_id, media_id HAVING c > 1;

-- 2) 加唯一约束
ALTER TABLE rating ADD CONSTRAINT uq_user_media UNIQUE (user_id, media_id);
